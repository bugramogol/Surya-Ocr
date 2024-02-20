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

# Create a dictionary to map language names to codes
with open("languages.json", "r") as file:
    languages = json.load(file)
language_dict = {name: code for name, code in languages.items()}

# Use the language names for the dropdown choices
language_options = list(language_dict.keys())

def ocr_function(img, lang_name):
    # Get the language code from the dictionary
    lang_code = language_dict[lang_name]
    predictions = run_ocr([img], [lang_code], det_model, det_processor, rec_model, rec_processor)
    # Assuming predictions is a list of dictionaries, one per image
    if predictions:
        img_with_text = draw_polys_on_image(predictions[0]["polys"], img)
        return img_with_text, predictions[0]["text"]
    else:
        return img, "No text detected"

def text_line_detection_function(img):
    preds = batch_detection([img], det_model, det_processor)[0]
    img_with_lines = draw_polys_on_image(preds["polygons"], img)
    return img_with_lines, preds

with gr.Blocks() as app:
    gr.Markdown("# Surya OCR and Text Line Detection")
    with gr.Tab("OCR"):
        with gr.Column():
            ocr_input_image = gr.Image(label="Input Image for OCR", type="pil")
            ocr_language_selector = gr.Dropdown(label="Select Language for OCR", choices=language_options, value="English")
            ocr_run_button = gr.Button("Run OCR")
        with gr.Column():
            ocr_output_image = gr.Image(label="OCR Output Image", type="pil", interactive=False)
            ocr_text_output = gr.TextArea(label="Recognized Text")

        # Pass the input image and the language name to the ocr_function
        ocr_run_button.click(fn=ocr_function, inputs=[ocr_input_image, ocr_language_selector], outputs=[ocr_output_image, ocr_text_output])

    with gr.Tab("Text Line Detection"):
        with gr.Column():
            detection_input_image = gr.Image(label="Input Image for Detection", type="pil")
            detection_run_button = gr.Button("Run Text Line Detection")
        with gr.Column():
            detection_output_image = gr.Image(label="Detection Output Image", type="pil", interactive=False)
            detection_json_output = gr.JSON(label="Detection JSON Output")

        # Pass the input image to the text_line_detection_function
        detection_run_button.click(fn=text_line_detection_function, inputs=detection_input_image, outputs=[detection_output_image, detection_json_output])

if __name__ == "__main__":
    app.launch()
