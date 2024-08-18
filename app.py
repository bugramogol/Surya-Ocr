import gradio as gr
import logging
import os
import json
from PIL import Image
import torch
from surya.ocr import run_ocr
from surya.detection import batch_text_detection
from surya.layout import batch_layout_detection
from surya.ordering import batch_ordering
from surya.model.detection.model import load_model as load_det_model, load_processor as load_det_processor
from surya.model.recognition.model import load_model as load_rec_model
from surya.model.recognition.processor import load_processor as load_rec_processor
from surya.settings import settings
from surya.model.ordering.processor import load_processor as load_order_processor
from surya.model.ordering.model import load_model as load_order_model

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Set environment variables for performance
os.environ["RECOGNITION_BATCH_SIZE"] = "512"
os.environ["DETECTOR_BATCH_SIZE"] = "36"
os.environ["ORDER_BATCH_SIZE"] = "32"
os.environ["RECOGNITION_STATIC_CACHE"] = "true"

# Load models
logger.info("Loading models...")
det_processor, det_model = load_det_processor(), load_det_model()
rec_model, rec_processor = load_rec_model(), load_rec_processor()
layout_model = load_det_model(checkpoint=settings.LAYOUT_MODEL_CHECKPOINT)
layout_processor = load_det_processor(checkpoint=settings.LAYOUT_MODEL_CHECKPOINT)
order_model = load_order_model()
order_processor = load_order_processor()

# Compile recognition model
logger.info("Compiling recognition model...")
rec_model.decoder.model = torch.compile(rec_model.decoder.model)

def ocr_workflow(image, langs):
    logger.info(f"Starting OCR workflow with languages: {langs}")
    image = Image.open(image.name)
    predictions = run_ocr([image], [langs.split(',')], det_model, det_processor, rec_model, rec_processor)
    logger.info("OCR workflow completed")
    return json.dumps(predictions, indent=2)

def text_detection_workflow(image):
    logger.info("Starting text detection workflow")
    image = Image.open(image.name)
    predictions = batch_text_detection([image], det_model, det_processor)
    logger.info("Text detection workflow completed")
    return json.dumps(predictions, indent=2)

def layout_analysis_workflow(image):
    logger.info("Starting layout analysis workflow")
    image = Image.open(image.name)
    line_predictions = batch_text_detection([image], det_model, det_processor)
    layout_predictions = batch_layout_detection([image], layout_model, layout_processor, line_predictions)
    logger.info("Layout analysis workflow completed")
    return json.dumps(layout_predictions, indent=2)

def reading_order_workflow(image):
    logger.info("Starting reading order workflow")
    image = Image.open(image.name)
    line_predictions = batch_text_detection([image], det_model, det_processor)
    layout_predictions = batch_layout_detection([image], layout_model, layout_processor, line_predictions)
    bboxes = [pred['bbox'] for pred in layout_predictions[0]['bboxes']]
    order_predictions = batch_ordering([image], [bboxes], order_model, order_processor)
    logger.info("Reading order workflow completed")
    return json.dumps(order_predictions, indent=2)

with gr.Blocks(theme=gr.themes.Soft()) as demo:
    gr.Markdown("# Surya Document Analysis")
    
    with gr.Tab("OCR"):
        gr.Markdown("## Optical Character Recognition")
        with gr.Row():
            ocr_input = gr.File(label="Upload Image or PDF")
            ocr_langs = gr.Textbox(label="Languages (comma-separated)", value="en")
        ocr_button = gr.Button("Run OCR")
        ocr_output = gr.JSON(label="OCR Results")
        ocr_button.click(ocr_workflow, inputs=[ocr_input, ocr_langs], outputs=ocr_output)

    with gr.Tab("Text Detection"):
        gr.Markdown("## Text Line Detection")
        det_input = gr.File(label="Upload Image or PDF")
        det_button = gr.Button("Run Text Detection")
        det_output = gr.JSON(label="Text Detection Results")
        det_button.click(text_detection_workflow, inputs=det_input, outputs=det_output)

    with gr.Tab("Layout Analysis"):
        gr.Markdown("## Layout Analysis and Reading Order")
        layout_input = gr.File(label="Upload Image or PDF")
        layout_button = gr.Button("Run Layout Analysis")
        order_button = gr.Button("Determine Reading Order")
        layout_output = gr.JSON(label="Layout Analysis Results")
        order_output = gr.JSON(label="Reading Order Results")
        layout_button.click(layout_analysis_workflow, inputs=layout_input, outputs=layout_output)
        order_button.click(reading_order_workflow, inputs=layout_input, outputs=order_output)

if __name__ == "__main__":
    logger.info("Starting Gradio app...")
    demo.launch()
