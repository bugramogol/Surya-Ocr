import gradio as gr
import json
import subprocess
from PIL import Image
import os
import tempfile
import sys
sys.setdefaultencoding('utf-8')

# Função auxiliar para salvar imagem temporariamente e retornar o caminho
def save_temp_image(img):
    temp_dir = tempfile.mkdtemp()
    img_path = os.path.join(temp_dir, "input_image.png")
    img.save(img_path)
    return img_path, temp_dir

# Função para executar o OCR via linha de comando
def ocr_function_cli(img, lang_name):
    img_path, temp_dir = save_temp_image(img)
    
    # Substitua 'surya_ocr' pelo comando correto no seu sistema
    command = f"surya_ocr {img_path} --langs {lang_name} --images --results_dir {temp_dir}"
    
    # Executar o comando
    subprocess.run(command, shell=True, check=True)
    
    # Aqui você precisa ajustar os caminhos conforme a saída do seu comando
    result_img_path = os.path.join(temp_dir, "image_with_text.png")  # Ajuste conforme necessário
    result_text_path = os.path.join(temp_dir, "results.json")  # Ajuste conforme necessário
    
    # Carregar a imagem resultante
    if os.path.exists(result_img_path):
        result_img = Image.open(result_img_path)
    else:
        result_img = img  # Retorna a imagem original se não encontrar a imagem processada
    
    # Carregar o texto resultante
    if os.path.exists(result_text_path):
        with open(result_text_path, "r") as file:
            result_text = json.load(file)
            # Ajuste a extração do texto conforme o formato do seu JSON
            text_output = "\n".join([str(page) for page in result_text.values()])
    else:
        text_output = "No text detected"
    
    # Limpeza
    os.remove(img_path)  # Remove a imagem temporária
    # opcional: remover diretório temporário e seus conteúdos, se necessário
    
    return result_img, text_output

# Função para detecção de linhas de texto via linha de comando
def text_line_detection_function_cli(img):
    img_path, temp_dir = save_temp_image(img)
    
    # Substitua 'surya_detect' pelo comando correto no seu sistema
    command = f"surya_detect {img_path} --images --results_dir {temp_dir}"
    
    # Executar o comando
    subprocess.run(command, shell=True, check=True)
    
    # Aqui você precisa ajustar os caminhos conforme a saída do seu comando
    result_img_path = os.path.join(temp_dir, "image_with_lines.png")  # Ajuste conforme necessário
    result_json_path = os.path.join(temp_dir, "results.json")  # Ajuste conforme necessário
    
    # Carregar a imagem resultante
    if os.path.exists(result_img_path):
        result_img = Image.open(result_img_path)
    else:
        result_img = img  # Retorna a imagem original se não encontrar a imagem processada
    
    # Carregar os resultados JSON
    if os.path.exists(result_json_path):
        with open(result_json_path, "r") as file:
            result_json = json.load(file)
    else:
        result_json = {"error": "No detection results found"}
    
    # Limpeza
    os.remove(img_path)  # Remove a imagem temporária
    # opcional: remover diretório temporário e seus conteúdos, se necessário
    
    return result_img, result_json

# Interface Gradio
with gr.Blocks() as app:
    gr.Markdown("# Surya OCR e Detecção de Linhas de Texto via CLI")
    with gr.Tab("OCR"):
        with gr.Column():
            ocr_input_image = gr.Image(label="Imagem de Entrada para OCR", type="pil")
            ocr_language_selector = gr.Dropdown(label="Selecione o Idioma para OCR", choices=["English", "Portuguese"], value="English")
            ocr_run_button = gr.Button("Executar OCR")
        with gr.Column():
            ocr_output_image = gr.Image(label="Imagem de Saída do OCR", type="pil", interactive=False)
            ocr_text_output = gr.TextArea(label="Texto Reconhecido")

        ocr_run_button.click(fn=ocr_function_cli, inputs=[ocr_input_image, ocr_language_selector], outputs=[ocr_output_image, ocr_text_output])

    with gr.Tab("Detecção de Linhas de Texto"):
        with gr.Column():
            detection_input_image = gr.Image(label="Imagem de Entrada para Detecção", type="pil")
            detection_run_button = gr.Button("Executar Detecção de Linhas de Texto")
        with gr.Column():
            detection_output_image = gr.Image(label="Imagem de Saída da Detecção", type="pil", interactive=False)
            detection_json_output = gr.JSON(label="Saída JSON da Detecção")

        detection_run_button.click(fn=text_line_detection_function_cli, inputs=detection_input_image, outputs=[detection_output_image, detection_json_output])

if __name__ == "__main__":
    app.launch()
