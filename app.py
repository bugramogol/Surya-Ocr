import gradio as gr
import json
from PIL import Image
# Assuming these imports work as expected, but you might need to adjust based on your actual package structure
from surya.ocr import run_ocr
from surya.detection import batch_detection
from surya.model.detection.segformer import load_model as load_det_model, load_processor as load_det_processor
from surya.model.recognition.model import load_model as load_rec_model
from surya.model.recognition.processor import load_processor as load_rec_processor
from surya.postprocessing.heatmap import draw_polys_on_image

# Load models and processors with print statements to confirm loading
print("Loading models and processors...")
det_model, det_processor = load_det_model(), load_det_processor()
rec_model, rec_processor = load_rec_model(), load_rec_processor()
print("Models and processors loaded successfully.")

# Load language codes
print("Loading language codes...")
with open("languages.json", "r") as file:
    languages = json.load(file)
language_dict = {name: code for name, code in languages.items()}
print(f"Loaded languages: {list(language_dict.keys())}")

def ocr_function(img, lang_name):
    print(f"OCR Function Called with lang_name: {lang_name}")
    lang_code = language_dict[lang_name]
    print(f"Language Code: {lang_code}")
    # Ensure langs is a list of language codes, not a list of lists
    predictions = run_ocr([img], [lang_code], det_model, det_processor, rec_model, rec_processor)  # Corrected
    print(f"Predictions: {predictions}")
    if predictions:
        img_with_text = draw_polys_on_image(predictions[0]["polys"], img)
        return img_with_text, predictions[0]["text"]
    else:
        return img, "No text detected"


def text_line_detection_function(img):
    print("Text Line Detection Function Called")
    preds = batch_detection([img], det_model, det_processor)[0]  # Assuming this returns a DetectionResult object
    print(f"Detection Predictions: {preds}")
    
    # Check if preds has an attribute 'bboxes' and use it
    if hasattr(preds, 'bboxes'):
        # Assuming draw_polys_on_image can work with the format of bboxes directly or you adapt it accordingly
        img_with_lines = draw_polys_on_image([bbox.polygon for bbox in preds.bboxes], img)
        return img_with_lines, preds
    else:
        raise AttributeError("DetectionResult object does not have 'bboxes' attribute")



with gr.Blocks() as app:
    gr.Markdown("# Surya OCR and Text Line Detection")
    with gr.Tab("OCR"):
        with gr.Column():
            ocr_input_image = gr.Image(label="Input Image for OCR", type="pil")
            ocr_language_selector = gr.Dropdown(label="Select Language for OCR", choices=list(language_dict.keys()), value="English")
            ocr_run_button = gr.Button("Run OCR")
        with gr.Column():
            ocr_output_image = gr.Image(label="OCR Output Image", type="pil", interactive=False)
            ocr_text_output = gr.TextArea(label="Recognized Text")

        ocr_run_button.click(fn=ocr_function, inputs=[ocr_input_image, ocr_language_selector], outputs=[ocr_output_image, ocr_text_output])

    with gr.Tab("Text Line Detection"):
        with gr.Column():
            detection_input_image = gr.Image(label="Input Image for Detection", type="pil")
            detection_run_button = gr.Button("Run Text Line Detection")
        with gr.Column():
            detection_output_image = gr.Image(label="Detection Output Image", type="pil", interactive=False)
            detection_json_output = gr.JSON(label="Detection JSON Output")

        detection_run_button.click(fn=text_line_detection_function, inputs=detection_input_image, outputs=[detection_output_image, detection_json_output])

if __name__ == "__main__":
    app.launch()
