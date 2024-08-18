import gradio as gr
import logging
import os
import json
from PIL import Image, ImageDraw
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

# Configuração do TorchDynamo
torch._dynamo.config.capture_scalar_outputs = True

# Configuração de logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Configuração de variáveis de ambiente
logger.info("Configurando variáveis de ambiente para otimização de performance")
os.environ["RECOGNITION_BATCH_SIZE"] = "512"
os.environ["DETECTOR_BATCH_SIZE"] = "36"
os.environ["ORDER_BATCH_SIZE"] = "32"
os.environ["RECOGNITION_STATIC_CACHE"] = "true"

# Carregamento de modelos
logger.info("Iniciando carregamento dos modelos...")

try:
    logger.debug("Carregando modelo e processador de detecção...")
    det_processor, det_model = load_det_processor(), load_det_model()
    logger.debug("Modelo e processador de detecção carregados com sucesso")
except Exception as e:
    logger.error(f"Erro ao carregar modelo de detecção: {e}")
    raise

try:
    logger.debug("Carregando modelo e processador de reconhecimento...")
    rec_model, rec_processor = load_rec_model(), load_rec_processor()
    logger.debug("Modelo e processador de reconhecimento carregados com sucesso")
except Exception as e:
    logger.error(f"Erro ao carregar modelo de reconhecimento: {e}")
    raise

try:
    logger.debug("Carregando modelo e processador de layout...")
    layout_model = load_det_model(checkpoint=settings.LAYOUT_MODEL_CHECKPOINT)
    layout_processor = load_det_processor(checkpoint=settings.LAYOUT_MODEL_CHECKPOINT)
    logger.debug("Modelo e processador de layout carregados com sucesso")
except Exception as e:
    logger.error(f"Erro ao carregar modelo de layout: {e}")
    raise

try:
    logger.debug("Carregando modelo e processador de ordenação...")
    order_model = load_order_model()
    order_processor = load_order_processor()
    logger.debug("Modelo e processador de ordenação carregados com sucesso")
except Exception as e:
    logger.error(f"Erro ao carregar modelo de ordenação: {e}")
    raise

logger.info("Todos os modelos foram carregados com sucesso")

# Compilação do modelo de reconhecimento
logger.info("Iniciando compilação do modelo de reconhecimento...")
try:
    rec_model.decoder.model = torch.compile(rec_model.decoder.model)
    logger.info("Compilação do modelo de reconhecimento concluída com sucesso")
except Exception as e:
    logger.error(f"Erro durante a compilação do modelo de reconhecimento: {e}")
    logger.warning("Continuando sem compilação do modelo")

class CustomJSONEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Image.Image):
            return "Image object (not serializable)"
        if hasattr(obj, '__dict__'):
            return obj.__dict__
        return super().default(obj)

def serialize_result(result):
    return json.dumps(result, cls=CustomJSONEncoder, indent=2)

def draw_boxes(image, predictions, color=(255, 0, 0)):
    draw = ImageDraw.Draw(image)
    for pred in predictions:
        bbox = pred.get('bbox') or pred.get('polygon')
        if bbox:
            draw.rectangle(bbox, outline=color, width=2)
    return image

def ocr_workflow(image, langs):
    logger.info(f"Iniciando workflow OCR com idiomas: {langs}")
    try:
        image = Image.open(image.name)
        logger.debug(f"Imagem carregada: {image.size}")
        predictions = run_ocr([image], [langs.split(',')], det_model, det_processor, rec_model, rec_processor)
        
        # Draw bounding boxes on the image
        image_with_boxes = draw_boxes(image.copy(), predictions[0]['text_lines'])
        
        # Format the OCR results
        formatted_text = "\n".join([line['text'] for line in predictions[0]['text_lines']])
        
        logger.info("Workflow OCR concluído com sucesso")
        return serialize_result(predictions), image_with_boxes, formatted_text
    except Exception as e:
        logger.error(f"Erro durante o workflow OCR: {e}")
        return serialize_result({"error": str(e)}), None, ""

def text_detection_workflow(image):
    logger.info("Iniciando workflow de detecção de texto")
    try:
        image = Image.open(image.name)
        logger.debug(f"Imagem carregada: {image.size}")
        predictions = batch_text_detection([image], det_model, det_processor)
        
        # Draw bounding boxes on the image
        image_with_boxes = draw_boxes(image.copy(), predictions[0].bboxes)
        
        logger.info("Workflow de detecção de texto concluído com sucesso")
        return serialize_result(predictions), image_with_boxes
    except Exception as e:
        logger.error(f"Erro durante o workflow de detecção de texto: {e}")
        return serialize_result({"error": str(e)}), None

def layout_analysis_workflow(image):
    logger.info("Iniciando workflow de análise de layout")
    try:
        image = Image.open(image.name)
        logger.debug(f"Imagem carregada: {image.size}")
        line_predictions = batch_text_detection([image], det_model, det_processor)
        logger.debug(f"Detecção de linhas concluída. Número de linhas detectadas: {len(line_predictions[0].bboxes)}")
        layout_predictions = batch_layout_detection([image], layout_model, layout_processor, line_predictions)
        
        # Draw bounding boxes on the image
        image_with_boxes = draw_boxes(image.copy(), layout_predictions[0].bboxes, color=(0, 255, 0))
        
        logger.info("Workflow de análise de layout concluído com sucesso")
        return serialize_result(layout_predictions), image_with_boxes
    except Exception as e:
        logger.error(f"Erro durante o workflow de análise de layout: {e}")
        return serialize_result({"error": str(e)}), None

def reading_order_workflow(image):
    logger.info("Iniciando workflow de ordem de leitura")
    try:
        image = Image.open(image.name)
        logger.debug(f"Imagem carregada: {image.size}")
        line_predictions = batch_text_detection([image], det_model, det_processor)
        logger.debug(f"Detecção de linhas concluída. Número de linhas detectadas: {len(line_predictions[0].bboxes)}")
        layout_predictions = batch_layout_detection([image], layout_model, layout_processor, line_predictions)
        logger.debug(f"Análise de layout concluída. Número de elementos de layout: {len(layout_predictions[0].bboxes)}")
        bboxes = [pred.bbox for pred in layout_predictions[0].bboxes]
        order_predictions = batch_ordering([image], [bboxes], order_model, order_processor)
        
        # Draw bounding boxes on the image
        image_with_boxes = image.copy()
        for i, bbox in enumerate(order_predictions[0]['bboxes']):
            draw = ImageDraw.Draw(image_with_boxes)
            draw.rectangle(bbox['bbox'], outline=(0, 0, 255), width=2)
            draw.text((bbox['bbox'][0], bbox['bbox'][1]), str(bbox['position']), fill=(255, 0, 0))
        
        logger.info("Workflow de ordem de leitura concluído com sucesso")
        return serialize_result(order_predictions), image_with_boxes
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
        ocr_output = gr.JSON(label="Resultados OCR")
        ocr_image = gr.Image(label="Imagem com Bounding Boxes")
        ocr_text = gr.Textbox(label="Texto Extraído", lines=10)
        ocr_button.click(ocr_workflow, inputs=[ocr_input, ocr_langs], outputs=[ocr_output, ocr_image, ocr_text])

    with gr.Tab("Detecção de Texto"):
        gr.Markdown("## Detecção de Linhas de Texto")
        det_input = gr.File(label="Carregar Imagem ou PDF")
        det_button = gr.Button("Executar Detecção de Texto")
        det_output = gr.JSON(label="Resultados da Detecção de Texto")
        det_image = gr.Image(label="Imagem com Bounding Boxes")
        det_button.click(text_detection_workflow, inputs=det_input, outputs=[det_output, det_image])

    with gr.Tab("Análise de Layout"):
        gr.Markdown("## Análise de Layout e Ordem de Leitura")
        layout_input = gr.File(label="Carregar Imagem ou PDF")
        layout_button = gr.Button("Executar Análise de Layout")
        order_button = gr.Button("Determinar Ordem de Leitura")
        layout_output = gr.JSON(label="Resultados da Análise de Layout")
        layout_image = gr.Image(label="Imagem com Layout")
        order_output = gr.JSON(label="Resultados da Ordem de Leitura")
        order_image = gr.Image(label="Imagem com Ordem de Leitura")
        layout_button.click(layout_analysis_workflow, inputs=layout_input, outputs=[layout_output, layout_image])
        order_button.click(reading_order_workflow, inputs=layout_input, outputs=[order_output, order_image])

if __name__ == "__main__":
    logger.info("Iniciando aplicativo Gradio...")
    demo.launch()
