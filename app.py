import gradio as gr
import torch
import logging
import os
import json
from PIL import Image
from surya.ocr import run_ocr
from surya.detection import batch_text_detection
from surya.layout import batch_layout_detection
from surya.ordering import batch_ordering
from surya.model.detection.model import load_model as load_det_model, load_processor as load_det_processor
from surya.model.recognition.model import load_model as load_rec_model
from surya.model.recognition.processor import load_processor as load_rec_processor
from surya.model.ordering.model import load_model as load_order_model
from surya.model.ordering.processor import load_processor as load_order_processor
from surya.settings import settings

# Set up logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Load models and processors
logger.info("Loading models and processors...")
det_processor, det_model = load_det_processor(), load_det_model()
rec_model, rec_processor = load_rec_model(), load_rec_processor()
layout_model = load_det_model(checkpoint=settings.LAYOUT_MODEL_CHECKPOINT)
layout_processor = load_det_processor(checkpoint=settings.LAYOUT_MODEL_CHECKPOINT)
order_model = load_order_model()
order_processor = load_order_processor()

# Compile the OCR model for better performance
logger.info("Compiling OCR model...")
os.environ['RECOGNITION_STATIC_CACHE'] = 'true'
rec_model.decoder.model = torch.compile(rec_model.decoder.model)

def process_image(image_path, langs):
    logger.info(f"Processing image: {image_path}")
    image = Image.open(image_path)
    
    # OCR
    logger.info("Performing OCR...")
    ocr_predictions = run_ocr([image], [langs.split(',')], det_model, det_processor, rec_model, rec_processor)
    
    # Text line detection
    logger.info("Detecting text lines...")
    line_predictions = batch_text_detection([image], det_model, det_processor)
    
    # Layout analysis
    logger.info("Analyzing layout...")
    layout_predictions = batch_layout_detection([image], layout_model, layout_processor, line_predictions)
    
    # Reading order
    logger.info("Determining reading order...")
    bboxes = [bbox['bbox'] for bbox in layout_predictions[0]['bboxes']]
    order_predictions = batch_ordering([image], [bboxes], order_model, order_processor)
    
    # Combine results
    results = {
        "ocr": ocr_predictions[0],
        "text_lines": line_predictions[0],
        "layout": layout_predictions[0],
        "reading_order": order_predictions[0]
    }
    
    logger.info("Processing complete.")
    return json.dumps(results, indent=2)

def surya_ui(image, langs):
    if image is None:
        return "Please upload an image."
    
    try:
        result = process_image(image, langs)
        return result
    except Exception as e:
        logger.error(f"Error processing image: {str(e)}")
        return f"An error occurred: {str(e)}"

# Create Gradio interface
iface = gr.Interface(
    fn=surya_ui,
    inputs=[
        gr.Image(type="filepath", label="Upload Image"),
        gr.Textbox(label="Languages (comma-separated, e.g., 'en,fr')", value="en")
    ],
    outputs=gr.Textbox(label="Results"),
    title="Surya Document Analysis",
    description="Upload an image to perform OCR, text line detection, layout analysis, and reading order detection.",
    theme="huggingface",
    css="""
    .gradio-container {
        font-family: 'IBM Plex Sans', sans-serif;
    }
    .gr-button {
        color: white;
        border-radius: 8px;
        background: linear-gradient(45deg, #ff9a9e 0%, #fad0c4 99%, #fad0c4 100%);
    }
    .gr-button:hover {
        background: linear-gradient(45deg, #fad0c4 0%, #ff9a9e 99%, #ff9a9e 100%);
    }
    .gr-form {
        border-radius: 12px;
        background-color: #ffffff;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
    }
    """
)

# Launch the interface
if __name__ == "__main__":
    logger.info("Starting Gradio interface...")
    iface.launch()
