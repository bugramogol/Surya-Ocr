import flask
from flask import Flask, request, jsonify
import logging
import os
import json
import tempfile
from PIL import Image
import torch
from surya.ocr import run_ocr
from surya.model.detection.model import load_model as load_det_model, load_processor as load_det_processor
from surya.model.recognition.model import load_model as load_rec_model
from surya.model.recognition.processor import load_processor as load_rec_processor

# Configure TorchDynamo
torch._dynamo.config.capture_scalar_outputs = True

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Configure environment variables
logger.info("Configuring environment variables for performance optimization")
os.environ["RECOGNITION_BATCH_SIZE"] = "512"
os.environ["DETECTOR_BATCH_SIZE"] = "36"
os.environ["ORDER_BATCH_SIZE"] = "32"
os.environ["RECOGNITION_STATIC_CACHE"] = "true"

# Initialize Flask app
app = Flask(__name__)

# Load models
logger.info("Loading OCR models...")

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

# Compile recognition model
logger.info("Compiling recognition model...")
try:
    rec_model.decoder.model = torch.compile(rec_model.decoder.model)
    logger.info("Recognition model compilation completed successfully")
except Exception as e:
    logger.error(f"Error during recognition model compilation: {e}")
    logger.warning("Continuing without model compilation")

class CustomJSONEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Image.Image):
            return "Image object (not serializable)"
        if hasattr(obj, '__dict__'):
            return {k: self.default(v) for k, v in obj.__dict__.items()}
        return str(obj)

@app.route('/', methods=['GET'])
def home():
    return jsonify({
        "status": "ok",
        "message": "Surya OCR API is running",
        "endpoints": {
            "/ocr": "POST - Perform OCR on an image file"
        }
    })

@app.route('/ocr', methods=['POST'])
def ocr():
    try:
        # Check if the request has an image file
        if 'image' not in request.files:
            return jsonify({'error': 'No image provided'}), 400
        
        file = request.files['image']
        if file.filename == '':
            return jsonify({'error': 'No image selected'}), 400
        
        # Get languages from request or use default
        langs = request.form.get('langs', 'en').split(',')
        
        # Save the uploaded file temporarily
        with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(file.filename)[1]) as temp:
            file.save(temp.name)
            temp_filename = temp.name
        
        try:
            # Process the image
            image = Image.open(temp_filename)
            logger.info(f"Image loaded: {image.size}")
            
            # Run OCR
            predictions = run_ocr([image], [langs], det_model, det_processor, rec_model, rec_processor)
            
            # Format the OCR results
            results = {
                'text': "\n".join([line.text for line in predictions[0].text_lines]),
                'details': []
            }
            
            # Add detailed information about each text line
            for line in predictions[0].text_lines:
                line_info = {
                    'text': line.text,
                    'bbox': line.bbox
                }
                results['details'].append(line_info)
            
            # Clean up the temporary file
            os.unlink(temp_filename)
            
            return jsonify(results)
        
        except Exception as e:
            # Make sure to clean up the temporary file in case of error
            if os.path.exists(temp_filename):
                os.unlink(temp_filename)
            logger.error(f"Error processing image: {e}")
            return jsonify({'error': str(e)}), 500
    
    except Exception as e:
        logger.error(f"Error in OCR endpoint: {e}")
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    logger.info("Starting Flask API server...")
    app.run(host='0.0.0.0', port=5000) 