import gradio as gr
import json
from PIL import Image
from surya.ocr import run_ocr
from surya.detection import batch_detection
from surya.model.detection.segformer import load_model as load_det_model, load_processor as load_det_processor
from surya.model.recognition.model import load_model as load_rec_model
from surya.model.recognition.processor import load_processor as load_rec_processor
from surya.postprocessing.heatmap import draw_polys_on_image

# Carregar modelos e processadores
det_model, det_processor = load_det_model(), load_det_processor()
rec_model, rec_processor = load_rec_model(), load_rec_processor()

# Carregar opções de idioma
with open("languages.json", "r") as file:
    languages = json.load(file)
language_options = [(language, code) for code, language in languages.items()]

def ocr_function(img, lang_code):
    # Ajuste aqui para garantir que lang_code é uma lista
    predictions = run_ocr([img], [lang_code], det_model, det_processor, rec_model, rec_processor)[0]
    img_with_text = draw_polys_on_image(predictions["polys"], img)
    return img_with_text, predictions["text"]

def text_line_detection_function(img):
    preds = batch_inference([img], det_model, det_processor)[0]
    img_with_lines = draw_polys_on_image(preds["polygons"], img)
    return img_with_lines, preds

with gr.Blocks() as app:
    gr.Markdown("# Surya OCR e Detecção de Linhas de Texto")
    with gr.Tab("OCR"):
        with gr.Column():
            ocr_input_image = gr.Image(label="Imagem de Entrada para OCR", type="pil")
            ocr_language_selector = gr.Dropdown(label="Selecione o Idioma para OCR", choices=language_options, value="en")
            ocr_run_button = gr.Button("Executar OCR")
        with gr.Column():
            ocr_output_image = gr.Image(label="Imagem de Saída do OCR", type="pil", interactive=False)
            ocr_text_output = gr.TextArea(label="Texto Reconhecido")

        ocr_run_button.click(fn=ocr_function, inputs=[ocr_input_image, ocr_language_selector], outputs=[ocr_output_image, ocr_text_output])

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
