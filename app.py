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

# Configuração de logging mais detalhada
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

def ocr_workflow(image, langs):
    logger.info(f"Iniciando workflow OCR com idiomas: {langs}")
    try:
        image = Image.open(image.name)
        logger.debug(f"Imagem carregada: {image.size}")
        predictions = run_ocr([image], [langs.split(',')], det_model, det_processor, rec_model, rec_processor)
        logger.info("Workflow OCR concluído com sucesso")
        return json.dumps(predictions, indent=2)
    except Exception as e:
        logger.error(f"Erro durante o workflow OCR: {e}")
        return json.dumps({"error": str(e)})

def text_detection_workflow(image):
    logger.info("Iniciando workflow de detecção de texto")
    try:
        image = Image.open(image.name)
        logger.debug(f"Imagem carregada: {image.size}")
        predictions = batch_text_detection([image], det_model, det_processor)
        logger.info("Workflow de detecção de texto concluído com sucesso")
        return json.dumps(predictions, indent=2)
    except Exception as e:
        logger.error(f"Erro durante o workflow de detecção de texto: {e}")
        return json.dumps({"error": str(e)})

def layout_analysis_workflow(image):
    logger.info("Iniciando workflow de análise de layout")
    try:
        image = Image.open(image.name)
        logger.debug(f"Imagem carregada: {image.size}")
        line_predictions = batch_text_detection([image], det_model, det_processor)
        logger.debug(f"Detecção de linhas concluída. Número de linhas detectadas: {len(line_predictions[0]['bboxes'])}")
        layout_predictions = batch_layout_detection([image], layout_model, layout_processor, line_predictions)
        logger.info("Workflow de análise de layout concluído com sucesso")
        return json.dumps(layout_predictions, indent=2)
    except Exception as e:
        logger.error(f"Erro durante o workflow de análise de layout: {e}")
        return json.dumps({"error": str(e)})

def reading_order_workflow(image):
    logger.info("Iniciando workflow de ordem de leitura")
    try:
        image = Image.open(image.name)
        logger.debug(f"Imagem carregada: {image.size}")
        line_predictions = batch_text_detection([image], det_model, det_processor)
        logger.debug(f"Detecção de linhas concluída. Número de linhas detectadas: {len(line_predictions[0]['bboxes'])}")
        layout_predictions = batch_layout_detection([image], layout_model, layout_processor, line_predictions)
        logger.debug(f"Análise de layout concluída. Número de elementos de layout: {len(layout_predictions[0]['bboxes'])}")
        bboxes = [pred['bbox'] for pred in layout_predictions[0]['bboxes']]
        order_predictions = batch_ordering([image], [bboxes], order_model, order_processor)
        logger.info("Workflow de ordem de leitura concluído com sucesso")
        return json.dumps(order_predictions, indent=2)
    except Exception as e:
        logger.error(f"Erro durante o workflow de ordem de leitura: {e}")
        return json.dumps({"error": str(e)})

with gr.Blocks(theme=gr.themes.Soft()) as demo:
    gr.Markdown("# Análise de Documentos com Surya")
    
    with gr.Tab("OCR"):
        gr.Markdown("## Reconhecimento Óptico de Caracteres")
        with gr.Row():
            ocr_input = gr.File(label="Carregar Imagem ou PDF")
            ocr_langs = gr.Textbox(label="Idiomas (separados por vírgula)", value="en")
        ocr_button = gr.Button("Executar OCR")
        ocr_output = gr.JSON(label="Resultados OCR")
        ocr_button.click(ocr_workflow, inputs=[ocr_input, ocr_langs], outputs=ocr_output)

    with gr.Tab("Detecção de Texto"):
        gr.Markdown("## Detecção de Linhas de Texto")
        det_input = gr.File(label="Carregar Imagem ou PDF")
        det_button = gr.Button("Executar Detecção de Texto")
        det_output = gr.JSON(label="Resultados da Detecção de Texto")
        det_button.click(text_detection_workflow, inputs=det_input, outputs=det_output)

    with gr.Tab("Análise de Layout"):
        gr.Markdown("## Análise de Layout e Ordem de Leitura")
        layout_input = gr.File(label="Carregar Imagem ou PDF")
        layout_button = gr.Button("Executar Análise de Layout")
        order_button = gr.Button("Determinar Ordem de Leitura")
        layout_output = gr.JSON(label="Resultados da Análise de Layout")
        order_output = gr.JSON(label="Resultados da Ordem de Leitura")
        layout_button.click(layout_analysis_workflow, inputs=layout_input, outputs=layout_output)
        order_button.click(reading_order_workflow, inputs=layout_input, outputs=order_output)

if __name__ == "__main__":
    logger.info("Iniciando aplicativo Gradio...")
    demo.launch()
