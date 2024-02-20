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

# Assuming languages.json maps language codes to names, but we'll use codes directly for dropdown
with open("languages.json", "r") as file:
    languages = json.load(file)
language_options = list(languages.keys())  # Use codes directly

def ocr_function(img, lang_code):
    predictions = run_ocr([img], [lang_code], det_model, det_processor, rec_model, rec_processor)
    # Assuming predictions is a list of dictionaries, one per image
    if predictions:
        img_with_text = draw_polys_on_image(predictions[0]["polys"], img)
        return img_with_text, predictions[0]
    else:
        return img, {"error": "No text detected"}

def text_line_detection_function(img):
    preds = batch_inference([img], det_model, det_processor)[0]
    img_with_lines = draw_polys_on_image(preds["polygons"], img)
    return img_with_lines, preds

with gr.Blocks() as app:
    gr.Markdown("# Surya OCR e Detecção de Linhas de Texto")
    with gr.Tab("OCR"):
        with gr.Column():
            ocr_input_image = gr.Image(label="Input Image for OCR", type="pil")
            ocr_language_selector = gr.Dropdown(label="Select Language for OCR", choices=language_options, value="en")
            ocr_run_button = gr.Button("Run OCR")
        with gr.Column():
            ocr_output_image = gr.Image(label="OCR Output Image", type="pil", interactive=False)
            ocr_text_output = gr.TextArea(label="Recognized Text")

        ocr_run_button.click(fn=ocr_function, inputs=[ocr_input_image, ocr_language_selector[0]], outputs=[ocr_output_image, ocr_text_output])


    with gr.Tab("Detecção de Linhas de Texto"):
        with gr.Column():
            detection_input_image = gr.Image(label="Imagem de Entrada para Detecção", type="pil")
            detection_run_button = gr.Button("Executar Detecção de Linhas de Texto")
        with gr.Column():
            detection_output_image = gr.Image(label="Imagem de Saída da Detecção", type="pil", interactive=False)
            detection_json_output = gr.JSON(label="Saída JSON da Detecção")

        detection_run_button.click(fn=text_line_detection_function, inputs=detection_input_image, outputs=[detection_output_image, detection_json_output])

if __name__ == "__main__":
    app.launch()
