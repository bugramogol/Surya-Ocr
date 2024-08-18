import gradio as gr
import logging
import os
import json
from PIL import Image, ImageDraw, ImageFont
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
from surya.model.ordering.model import load_order_model
import io

# Configuração de logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Configuração do TorchDynamo
torch._dynamo.config.capture_scalar_outputs = True

# Configuração de variáveis de ambiente
os.environ["RECOGNITION_BATCH_SIZE"] = "512"
os.environ["DETECTOR_BATCH_SIZE"] = "36"
os.environ["ORDER_BATCH_SIZE"] = "32"
os.environ["RECOGNITION_STATIC_CACHE"] = "true"

# Carregamento de modelos
logger.info("Iniciando carregamento dos modelos...")
det_processor, det_model = load_det_processor(), load_det_model()
rec_model, rec_processor = load_rec_model(), load_rec_processor()
layout_model = load_det_model(checkpoint=settings.LAYOUT_MODEL_CHECKPOINT)
layout_processor = load_det_processor(checkpoint=settings.LAYOUT_MODEL_CHECKPOINT)
order_model = load_order_model()
order_processor = load_order_processor()

# Compilação do modelo de reconhecimento
logger.info("Compilando modelo de reconhecimento...")
rec_model.decoder.model = torch.compile(rec_model.decoder.model)

class CustomJSONEncoder(json.JSONEncoder):
    def default(self, obj):
        if hasattr(obj, '__dict__'):
            return obj.__dict__
        return str(obj)

def serialize_result(result):
    return json.dumps(result, cls=CustomJSONEncoder, indent=2)

def draw_boxes(image, predictions):
    draw = ImageDraw.Draw(image)
    font = ImageFont.load_default()
    for idx, pred in enumerate(predictions[0]['text_lines']):
        bbox = pred['bbox']
        draw.rectangle(bbox, outline="red", width=2)
        draw.text((bbox[0], bbox[1] - 10), f"{idx+1}", font=font, fill="red")
    return image

def format_ocr_text(predictions):
    formatted_text = ""
    for idx, pred in enumerate(predictions[0]['text_lines']):
        formatted_text += f"{idx+1}. {pred['text']} (Confidence: {pred['confidence']:.2f})\n"
    return formatted_text

def ocr_workflow(image, langs):
    logger.info(f"Iniciando workflow OCR com idiomas: {langs}")
    try:
        image_pil = Image.open(image.name)
        predictions = run_ocr([image_pil], [langs.split(',')], det_model, det_processor, rec_model, rec_processor)
        logger.info("Workflow OCR concluído com sucesso")
        
        # Desenhar caixas na imagem
        image_with_boxes = draw_boxes(image_pil.copy(), predictions)
        
        # Formatar texto OCR
        formatted_text = format_ocr_text(predictions)
        
        return serialize_result(predictions), image_with_boxes, formatted_text
    except Exception as e:
        logger.error(f"Erro durante o workflow OCR: {e}")
        return serialize_result({"error": str(e)}), None, str(e)

def text_detection_workflow(image):
    logger.info("Iniciando workflow de detecção de texto")
    try:
        image_pil = Image.open(image.name)
        predictions = batch_text_detection([image_pil], det_model, det_processor)
        logger.info("Workflow de detecção de texto concluído com sucesso")
        
        # Desenhar caixas na imagem
        image_with_boxes = draw_boxes(image_pil.copy(), [{"text_lines": predictions[0].bboxes}])
        
        return serialize_result(predictions), image_with_boxes
    except Exception as e:
        logger.error(f"Erro durante o workflow de detecção de texto: {e}")
        return serialize_result({"error": str(e)}), None

def layout_analysis_workflow(image):
    logger.info("Iniciando workflow de análise de layout")
    try:
        image_pil = Image.open(image.name)
        line_predictions = batch_text_detection([image_pil], det_model, det_processor)
        layout_predictions = batch_layout_detection([image_pil], layout_model, layout_processor, line_predictions)
        logger.info("Workflow de análise de layout concluído com sucesso")
        
        # Desenhar caixas na imagem
        image_with_boxes = draw_boxes(image_pil.copy(), [{"text_lines": layout_predictions[0].bboxes}])
        
        return serialize_result(layout_predictions), image_with_boxes
    except Exception as e:
        logger.error(f"Erro durante o workflow de análise de layout: {e}")
        return serialize_result({"error": str(e)}), None

def reading_order_workflow(image):
    logger.info("Iniciando workflow de ordem de leitura")
    try:
        image_pil = Image.open(image.name)
        line_predictions = batch_text_detection([image_pil], det_model, det_processor)
        layout_predictions = batch_layout_detection([image_pil], layout_model, layout_processor, line_predictions)
        bboxes = [pred.bbox for pred in layout_predictions[0].bboxes]
        order_predictions = batch_ordering([image_pil], [bboxes], order_model, order_processor)
        logger.info("Workflow de ordem de leitura concluído com sucesso")
        
        # Desenhar caixas na imagem com a ordem de leitura
        image_with_order = image_pil.copy()
        draw = ImageDraw.Draw(image_with_order)
        font = ImageFont.load_default()
        for idx, bbox in enumerate(order_predictions[0]['bboxes']):
            draw.rectangle(bbox['bbox'], outline="blue", width=2)
            draw.text((bbox['bbox'][0], bbox['bbox'][1] - 10), f"{idx+1}", font=font, fill="blue")
        
        return serialize_result(order_predictions), image_with_order
    except Exception as e:
        logger.error(f"Erro durante o workflow de ordem de leitura: {e}")
        return serialize_result({"error": str(e)}), None

with gr.Blocks(theme=gr.themes.Soft()) as demo:
    gr.Markdown("# Análise de Documentos com Surya")
    
    with gr.Tab("OCR"):
        gr.Markdown("## Reconhecimento Óptico de Caracteres")
        with gr.Row():
            ocr_input = gr.File(label="Carregar Imagem ou PDF")
            ocr_langs = gr.Textbox(label="Idiomas (separados por vírgula)", value="en")
        ocr_button = gr.Button("Executar OCR")
        with gr.Row():
            ocr_output = gr.JSON(label="Resultados OCR")
            ocr_image = gr.Image(label="Imagem com Caixas")
        ocr_text = gr.Textbox(label="Texto Reconhecido", lines=10)
        ocr_button.click(ocr_workflow, inputs=[ocr_input, ocr_langs], outputs=[ocr_output, ocr_image, ocr_text])

    with gr.Tab("Detecção de Texto"):
        gr.Markdown("## Detecção de Linhas de Texto")
        det_input = gr.File(label="Carregar Imagem ou PDF")
        det_button = gr.Button("Executar Detecção de Texto")
        with gr.Row():
            det_output = gr.JSON(label="Resultados da Detecção de Texto")
            det_image = gr.Image(label="Imagem com Caixas")
        det_button.click(text_detection_workflow, inputs=det_input, outputs=[det_output, det_image])

    with gr.Tab("Análise de Layout"):
        gr.Markdown("## Análise de Layout e Ordem de Leitura")
        layout_input = gr.File(label="Carregar Imagem ou PDF")
        layout_button = gr.Button("Executar Análise de Layout")
        order_button = gr.Button("Determinar Ordem de Leitura")
        with gr.Row():
            layout_output = gr.JSON(label="Resultados da Análise de Layout")
            layout_image = gr.Image(label="Imagem com Layout")
        with gr.Row():
            order_output = gr.JSON(label="Resultados da Ordem de Leitura")
            order_image = gr.Image(label="Imagem com Ordem de Leitura")
        layout_button.click(layout_analysis_workflow, inputs=layout_input, outputs=[layout_output, layout_image])
        order_button.click(reading_order_workflow, inputs=layout_input, outputs=[order_output, order_image])

if __name__ == "__main__":
    logger.info("Iniciando aplicativo Gradio...")
    demo.launch()
