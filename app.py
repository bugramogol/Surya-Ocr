import gradio as gr
import json
from PIL import Image
from surya.ocr import run_ocr
from surya.detection import batch_detection
from surya.model.detection.segformer import load_model as load_det_model, load_processor as load_det_processor
from surya.model.recognition.model import load_model as load_rec_model
from surya.model.recognition.processor import load_processor as load_rec_processor
from surya.postprocessing.heatmap import draw_polys_on_image

# Load models and processors
det_model, det_processor = load_det_model(), load_det_processor()
rec_model, rec_processor = load_rec_model(), load_rec_processor()

# Load languages from JSON
with open("languages.json", "r") as file:
    languages = json.load(file)
language_options = [(code, language) for code, language in languages.items()]

def ocr_function(img, langs):
    predictions = run_ocr([img], langs.split(','), det_model, det_processor, rec_model, rec_processor)[0]
    img_with_text = draw_polys_on_image(predictions["polys"], img)
    return img_with_text, predictions

def text_line_detection_function(img):
    preds = batch_detection([img], det_model, det_processor)[0]
    img_with_lines = draw_polys_on_image(preds["polygons"], img)
    return img_with_lines, preds

with gr.Blocks() as app:
    gr.Markdown("# Surya OCR and Text Line Detection Demo")
    with gr.Tab("OCR"):
        with gr.Row():
            ocr_input_image = gr.Image(label="Input Image for OCR", type="pil")
            ocr_language_selector = gr.Dropdown(label="Select Language(s) for OCR", choices=language_options, value="en", type="str")
            ocr_output_image = gr.Image(label="OCR Output Image", type="pil", interactive=False)
            ocr_json_output = gr.JSON(label="OCR JSON Output")
        ocr_button = gr.Button("Run OCR")
        ocr_button.click(fn=ocr_function, inputs=[ocr_input_image, ocr_language_selector], outputs=[ocr_output_image, ocr_json_output])

    with gr.Tab("Text Line Detection"):
        with gr.Row():
            detection_input_image = gr.Image(label="Input Image for Detection", type="pil")
            detection_output_image = gr.Image(label="Detection Output Image", type="pil", interactive=False)
            detection_json_output = gr.JSON(label="Detection JSON Output")
        detection_button = gr.Button("Run Text Line Detection")
        detection_button.click(fn=text_line_detection_function, inputs=detection_input_image, outputs=[detection_output_image, detection_json_output])

if __name__ == "__main__":
    app.launch()
