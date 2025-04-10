import os
import tempfile
import uuid
import json
import threading
import logging
from PIL import Image, ImageDraw
import torch
from flask import Flask, request, jsonify, render_template, send_from_directory
import requests
from werkzeug.utils import secure_filename
import time

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Check for GPU availability
device = os.environ.get('TORCH_DEVICE', 'cpu')
if device == 'cuda' and not torch.cuda.is_available():
    logger.warning("CUDA requested but not available. Fallback to CPU.")
    device = 'cpu'

# Configure torch to use CUDA if available
if device == 'cuda':
    logger.info("Setting PyTorch to use CUDA")
    os.environ["CUDA_VISIBLE_DEVICES"] = os.environ.get("CUDA_VISIBLE_DEVICES", "0")
    # Enable for Surya models
    os.environ["SURYA_USE_CUDA"] = "1"
    # Let PyTorch know to use CUDA
    torch.set_default_tensor_type('torch.cuda.FloatTensor')
else:
    logger.info("Using CPU for computations")
    os.environ["SURYA_USE_CUDA"] = "0"

logger.info(f"Using device: {device}")

# Surya OCR import - import after setting device
from surya.ocr import run_ocr
from surya.model.detection.model import load_model as load_det_model, load_processor as load_det_processor
from surya.model.recognition.model import load_model as load_rec_model
from surya.model.recognition.processor import load_processor as load_rec_processor

# TorchDynamo configuration
torch._dynamo.config.capture_scalar_outputs = True

# Configure environment variables
logger.info("Configuring environment variables for OCR performance optimization")
os.environ["RECOGNITION_BATCH_SIZE"] = os.environ.get("RECOGNITION_BATCH_SIZE", "512")
os.environ["DETECTOR_BATCH_SIZE"] = os.environ.get("DETECTOR_BATCH_SIZE", "36")
os.environ["ORDER_BATCH_SIZE"] = os.environ.get("ORDER_BATCH_SIZE", "32")
os.environ["RECOGNITION_STATIC_CACHE"] = "true"

if device == 'cuda':
    logger.info("GPU mode active, optimizing batch sizes")
    # Increase batch sizes for GPU
    os.environ["RECOGNITION_BATCH_SIZE"] = os.environ.get("RECOGNITION_BATCH_SIZE", "1024")
    os.environ["DETECTOR_BATCH_SIZE"] = os.environ.get("DETECTOR_BATCH_SIZE", "64")
    os.environ["ORDER_BATCH_SIZE"] = os.environ.get("ORDER_BATCH_SIZE", "64")
    # Additional GPU optimizations
    os.environ["PYTORCH_CUDA_ALLOC_CONF"] = os.environ.get("PYTORCH_CUDA_ALLOC_CONF", "max_split_size_mb:512")

# Configuration for the web application
UPLOAD_FOLDER = 'uploads'
PDF_FOLDER = 'pdf'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'tif', 'tiff', 'bmp'}
MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max upload size

# Create directories if they don't exist
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(PDF_FOLDER, exist_ok=True)
os.makedirs(os.path.join('static', 'temp'), exist_ok=True)

# Initialize Flask application
app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['PDF_FOLDER'] = PDF_FOLDER
app.config['MAX_CONTENT_LENGTH'] = MAX_CONTENT_LENGTH

# Global variables for OCR models
det_processor = None
det_model = None
rec_processor = None
rec_model = None

def load_ocr_models():
    """Load OCR models"""
    global det_processor, det_model, rec_processor, rec_model
    
    logger.info(f"Loading OCR models on {device}...")
    
    try:
        logger.info("Loading detection model and processor...")
        det_processor, det_model = load_det_processor(), load_det_model()
        logger.info("Detection model and processor loaded successfully")
    except Exception as e:
        logger.error(f"Error loading detection model: {e}")
        raise
    
    try:
        logger.info("Loading recognition model and processor...")
        rec_model, rec_processor = load_rec_model(), load_rec_processor()
        logger.info("Recognition model and processor loaded successfully")
    except Exception as e:
        logger.error(f"Error loading recognition model: {e}")
        raise
    
    # No need to compile on GPU - the models are already on the right device
    if device == 'cuda':
        logger.info("GPU mode active, skipping model compilation")
    elif os.environ.get("SKIP_COMPILE", "").lower() != "true":
        logger.info("Compiling recognition model...")
        try:
            rec_model.decoder.model = torch.compile(rec_model.decoder.model)
            logger.info("Recognition model compilation completed successfully")
        except Exception as e:
            logger.error(f"Error during recognition model compilation: {e}")
            logger.warning("Continuing without model compilation")
    else:
        logger.info("Skipping model compilation as requested by environment variable")

class CustomJSONEncoder(json.JSONEncoder):
    """Custom JSON encoder to handle PIL Image and other objects"""
    def default(self, obj):
        if isinstance(obj, Image.Image):
            return "Image object (not serializable)"
        if hasattr(obj, '__dict__'):
            return {k: self.default(v) for k, v in obj.__dict__.items()}
        return str(obj)

def process_ocr(image_path, langs):
    """Process image with OCR and generate PDF"""
    logger.info(f"Processing OCR for {image_path} with languages: {langs}")
    
    try:
        # Open the image
        image = Image.open(image_path)
        logger.info(f"Image loaded: {image.size}")
        
        # Convert languages string to list
        lang_list = langs.split(',')
        
        # Run OCR with GPU acceleration if available
        start_time = time.time()
        
        # GPU kullanımı için modelleri doğru cihaza taşıyoruz, ama run_ocr'a device parametresi gönderemiyoruz
        # O yüzden modeller zaten GPU'ya taşındıysa, GPU kullanılacaktır
        predictions = run_ocr([image], [lang_list], det_model, det_processor, rec_model, rec_processor)
        
        ocr_time = time.time() - start_time
        logger.info(f"OCR processing completed in {ocr_time:.2f} seconds on {device}")
        
        # Get extracted text
        text_content = "\n".join([line.text for line in predictions[0].text_lines])
        
        # Extract exact coordinates and text data as they appear in the OCR results
        text_lines = []
        for line in predictions[0].text_lines:
            # Ensure we're keeping the exact bbox format without any conversion
            bbox = line.bbox
            
            line_data = {
                'text': line.text,
                'bbox': bbox,  # Keep the original bbox format
                'polygon': line.polygon if hasattr(line, 'polygon') else None,
                'confidence': float(line.confidence) if hasattr(line, 'confidence') else None,
                'vertical': line.vertical if hasattr(line, 'vertical') else False
            }
            text_lines.append(line_data)
        
        # Generate PDF
        pdf_filename = f"{os.path.splitext(os.path.basename(image_path))[0]}_ocr.pdf"
        pdf_path = os.path.join(app.config['PDF_FOLDER'], pdf_filename)
        logger.info(f"Will create PDF at: {pdf_path}")
        
        # Ensure PDF directory exists
        os.makedirs(os.path.dirname(pdf_path), exist_ok=True)
        
        # Save PDF using reportlab with improved Unicode support
        from reportlab.pdfgen import canvas
        from reportlab.lib.pagesizes import A4
        from reportlab.pdfbase import pdfmetrics
        from reportlab.pdfbase.ttfonts import TTFont
        
        # List of potential Unicode fonts to try
        font_paths = [
            # Docker container paths
            '/app/fonts/DejaVuSans.ttf',
            '/app/fonts/Ubuntu-R.ttf',
            '/app/fonts/LiberationSans-Regular.ttf',
            '/app/fonts/FreeSans.ttf',
            # System paths
            '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',
            '/usr/local/share/fonts/dejavu/DejaVuSans.ttf',
            'C:\\Windows\\Fonts\\Arial.ttf',
            'C:\\Windows\\Fonts\\DejaVuSans.ttf',
            'C:\\Windows\\Fonts\\calibri.ttf',
            '/System/Library/Fonts/Helvetica.ttf'
        ]
        
        # Try to register the best font for Turkish
        font_registered = False
        registered_font_name = 'DefaultFont'
        
        for font_path in font_paths:
            if os.path.exists(font_path):
                font_name = os.path.splitext(os.path.basename(font_path))[0]
                try:
                    logger.info(f"Registering font: {font_name} from {font_path}")
                    pdfmetrics.registerFont(TTFont(font_name, font_path))
                    font_registered = True
                    registered_font_name = font_name
                    break
                except Exception as e:
                    logger.error(f"Error registering font {font_name}: {e}")
        
        if not font_registered:
            logger.warning("Could not register any Unicode font, falling back to Helvetica")
            registered_font_name = 'Helvetica'
            
        logger.info(f"Using font: {registered_font_name} for PDF generation")
        
        # PDF dimensions and preparation
        page_width, page_height = A4
        c = canvas.Canvas(pdf_path, pagesize=A4)
        
        # Get max image dimensions for scaling
        max_y = 0
        max_x = 0
        for line in predictions[0].text_lines:
            bbox = line.bbox
            max_x = max(max_x, bbox[2])
            max_y = max(max_y, bbox[3])
        
        # Calculate scaling factors
        available_width = page_width - 60  # margins
        available_height = page_height - 60
        scale_x = available_width / max_x
        scale_y = available_height / max_y
        scale_factor = min(scale_x, scale_y) * 0.95
        
        # Y-offset from the top
        y_offset = page_height - 30
        
        # Set font size
        avg_height = 0
        count = 0
        for line in predictions[0].text_lines:
            text_height = line.bbox[3] - line.bbox[1]
            if text_height > 0:
                avg_height += text_height
                count += 1
        
        font_size = 10  # Default
        if count > 0:
            avg_height = avg_height / count
            font_size = max(8, min(12, avg_height * scale_factor * 0.7))
        
        # Set the font
        c.setFont(registered_font_name, font_size)
        
        # Track successful text placement
        text_success_count = 0
        text_fallback_count = 0
        text_failed_count = 0
        
        # Add each text line with fallback handling
        for line in predictions[0].text_lines:
            text = line.text
            bbox = line.bbox
            
            pdf_x = 30 + (bbox[0] * scale_factor)
            pdf_y = y_offset - (bbox[1] * scale_factor)
            
            # Try multiple approaches to render text
            text_placed = False
            
            # First attempt: Try with registered Unicode font
            try:
                c.drawString(pdf_x, pdf_y, text)
                text_success_count += 1
                text_placed = True
            except:
                # If that failed, try with each registered font
                if font_registered:
                    try:
                        for font_path in font_paths:
                            if os.path.exists(font_path):
                                font_name = os.path.splitext(os.path.basename(font_path))[0]
                                try:
                                    # Try to register the font if not already registered
                                    if font_name != registered_font_name:
                                        pdfmetrics.registerFont(TTFont(font_name, font_path))
                                    
                                    # Try with this font
                                    c.setFont(font_name, font_size)
                                    c.drawString(pdf_x, pdf_y, text)
                                    text_fallback_count += 1
                                    text_placed = True
                                    
                                    # Reset to original font
                                    c.setFont(registered_font_name, font_size)
                                    break
                                except:
                                    # Continue to next font
                                    continue
                    except:
                        # If all font attempts failed, continue to next fallback
                        pass
                        
                # If still failed, try ASCII fallback
                if not text_placed:
                    try:
                        ascii_text = text.encode('ascii', 'replace').decode('ascii')
                        c.setFont('Helvetica', font_size)  # Use built-in font for ASCII
                        c.drawString(pdf_x, pdf_y, ascii_text)
                        c.setFont(registered_font_name, font_size)  # Reset to original font
                        logger.warning(f"Used ASCII fallback for text: {text}")
                        text_fallback_count += 1
                        text_placed = True
                    except:
                        # Last resort: use a placeholder
                        try:
                            c.setFont('Helvetica', font_size)
                            c.drawString(pdf_x, pdf_y, f"[Text at ({bbox[0]},{bbox[1]})]")
                            c.setFont(registered_font_name, font_size)
                            logger.error(f"Could not render text: {text}")
                            text_failed_count += 1
                            text_placed = True
                        except:
                            # If even this fails, just skip this text
                            logger.error(f"Failed completely to render text at position {bbox}")
        
        c.save()
        logger.info(f"PDF text rendering stats: Success={text_success_count}, Fallback={text_fallback_count}, Failed={text_failed_count}")
        logger.info(f"PDF saved to {pdf_path}")
        
        # After PDF creation
        if os.path.exists(pdf_path):
            logger.info(f"PDF created successfully at {pdf_path}, size: {os.path.getsize(pdf_path)} bytes")
        else:
            logger.error(f"Failed to create PDF at {pdf_path}")
        
        return {
            "text": text_content,
            "text_lines": text_lines,
            "pdfUrl": f"/pdf/{pdf_filename}"
        }
    
    except Exception as e:
        logger.error(f"Error in OCR processing: {e}")
        raise

# Helper function to check if a file extension is allowed
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# Helper function to visualize bounding boxes for debugging
def draw_boxes(image, text_lines, output_path):
    """Draw bounding boxes on image for visual verification"""
    try:
        draw = ImageDraw.Draw(image)
        for i, line in enumerate(text_lines):
            bbox = line['bbox']
            # Draw rectangle around text
            draw.rectangle(bbox, outline=(255, 0, 0), width=2)
            # Draw text position indicator
            draw.text((bbox[0], bbox[1] - 10), str(i), fill=(255, 0, 0))
        
        image.save(output_path)
        logger.info(f"Debug image with bounding boxes saved to {output_path}")
    except Exception as e:
        logger.error(f"Error drawing bounding boxes: {e}")

@app.route('/')
def index():
    """Render the main page"""
    return render_template('index.html')

@app.route('/api/ocr', methods=['POST'])
def api_ocr():
    """API endpoint for OCR processing"""
    # Check if the post request has the file part
    if 'image' not in request.files:
        return jsonify({'error': 'No image part'}), 400
    
    file = request.files['image']
    
    # If user does not select a file
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400
    
    if file and allowed_file(file.filename):
        # Create a secure filename
        filename = secure_filename(file.filename)
        unique_filename = f"{uuid.uuid4().hex}_{filename}"
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
        
        # Save the file temporarily
        file.save(file_path)
        
        try:
            # Get languages from request
            langs = request.form.get('langs', 'tr,en')
            
            # Process the image with OCR
            ocr_result = process_ocr(file_path, langs)
            
            # Optional: Generate debug image with bounding boxes
            debug_mode = request.form.get('debug', 'false').lower() == 'true'
            if debug_mode and 'text_lines' in ocr_result:
                debug_image_path = os.path.join('static', 'temp', f"debug_{os.path.basename(file_path)}")
                draw_boxes(Image.open(file_path), ocr_result['text_lines'], debug_image_path)
                ocr_result['debugImageUrl'] = f"/static/temp/{os.path.basename(debug_image_path)}"
            
            # Return the results with exact bbox coordinates
            return jsonify({
                'success': True,
                'text': ocr_result.get('text', ''),
                'text_lines': ocr_result.get('text_lines', []),
                'pdfUrl': ocr_result.get('pdfUrl', ''),
                'debugImageUrl': ocr_result.get('debugImageUrl', '') if debug_mode else ''
            })
            
        except Exception as e:
            return jsonify({'error': str(e)}), 500
        finally:
            # Clean up the uploaded file
            if os.path.exists(file_path):
                os.remove(file_path)
    
    return jsonify({'error': 'Invalid file format'}), 400

@app.route('/api/device-info')
def device_info():
    """Get device information (CPU/GPU)"""
    gpu_info = ""
    
    if device == 'cuda':
        try:
            gpu_name = torch.cuda.get_device_name(0)
            total_memory = torch.cuda.get_device_properties(0).total_memory / (1024**3)  # GB
            gpu_info = f"{gpu_name} ({total_memory:.1f}GB)"
        except Exception as e:
            logger.error(f"Error getting GPU info: {e}")
            gpu_info = "CUDA (unknown model)"
        
        return jsonify({
            'device': f"GPU: {gpu_info}",
            'is_gpu': True,
            'batch_sizes': {
                'recognition': os.environ.get("RECOGNITION_BATCH_SIZE"),
                'detection': os.environ.get("DETECTOR_BATCH_SIZE"),
                'ordering': os.environ.get("ORDER_BATCH_SIZE")
            }
        })
    else:
        import platform
        import multiprocessing
        
        cpu_info = platform.processor() or "Unknown CPU"
        cpu_count = multiprocessing.cpu_count()
        
        return jsonify({
            'device': f"CPU: {cpu_info} ({cpu_count} cores)",
            'is_gpu': False,
            'batch_sizes': {
                'recognition': os.environ.get("RECOGNITION_BATCH_SIZE"),
                'detection': os.environ.get("DETECTOR_BATCH_SIZE"),
                'ordering': os.environ.get("ORDER_BATCH_SIZE")
            }
        })

@app.route('/pdf/<filename>')
def serve_pdf(filename):
    """Serve a PDF file from the PDF folder"""
    logger.info(f"Attempting to serve PDF: {filename} from directory: {app.config['PDF_FOLDER']}")
    pdf_path = os.path.join(app.config['PDF_FOLDER'], filename)
    if os.path.exists(pdf_path):
        logger.info(f"PDF file found at: {pdf_path}")
    else:
        logger.error(f"PDF file not found at: {pdf_path}")
        # List files in PDF directory to debug
        try:
            pdf_files = os.listdir(app.config['PDF_FOLDER'])
            logger.info(f"Files in PDF directory: {pdf_files}")
        except Exception as e:
            logger.error(f"Error listing PDF directory: {e}")
    return send_from_directory(app.config['PDF_FOLDER'], filename)

if __name__ == '__main__':
    # Load OCR models before starting the Flask app
    logger.info("Starting Surya OCR API with Web Interface")
    load_ocr_models()
    logger.info("Models loaded, starting web server")
    
    # Run the Flask app
    app.run(host='0.0.0.0', port=5000, debug=False) 