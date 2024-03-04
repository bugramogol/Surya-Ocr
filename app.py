import gradio as gr
import json
import subprocess
from PIL import Image
import os
import tempfile
import logging

# Load language mappings from JSON file
with open("languages.json", "r", encoding='utf-8') as file:
    language_map = json.load(file)

# Configuração básica de logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def save_temp_image(img):
    temp_dir = tempfile.mkdtemp()
    img_path = os.path.join(temp_dir, "input_image.png")
    img.save(img_path)
    logging.info(f"Imagem salva em {img_path}")
    return img_path, temp_dir

def run_command(command):
    logging.info(f"Executing command: {command}")  # Adiciona o log do comando
    try:
        result = subprocess.check_output(command, shell=True, stderr=subprocess.STDOUT, encoding='utf-8')
        logging.info("Command Output: " + result)
        return result
    except subprocess.CalledProcessError as e:
        logging.error(f"Command failed with error: {e.output}")
        return None


def ocr_function_cli(img, lang_name):
    img_path, temp_dir = save_temp_image(img)

    # Get language abbreviation from language_map
    lang_code = language_map.get(lang_name, "en")  # Default to English if not found

    command = f"surya_ocr {img_path} --langs {lang_code} --images --results_dir {temp_dir}"
    if run_command(command) is None:
        return img, "OCR failed"

    result_img_path = os.path.join(temp_dir, "image_with_text.png")
    result_text_path = os.path.join(temp_dir, "results.json")

    if os.path.exists(result_img_path):
        result_img = Image.open(result_img_path)
    else:
        result_img = img

    if os.path.exists(result_text_path):
        with open(result_text_path, "r", encoding='utf-8') as file:
            result_text = json.load(file)
        text_output = "\n".join([str(page) for page in result_text.values()])
    else:
        text_output = "No text detected"

    # Limpeza movida para depois da leitura dos resultados
    os.remove(img_path)
    logging.info(f"Limpeza concluída para {img_path}")
    return result_img, text_output

def text_line_detection_function_cli(img):
    img_path, temp_dir = save_temp_image(img)
    command = f"surya_detect {img_path} --images --results_dir {temp_dir}"
    if run_command(command) is None:
        return img, {"error": "Detection failed"}

    result_img_path = os.path.join(temp_dir, "image_with_lines.png")
    result_json_path = os.path.join(temp_dir, "results.json")

    if os.path.exists(result_img_path):
        result_img = Image.open(result_img_path)
    else:
        result_img = img

    if os.path.exists(result_json_path):
        with open(result_json_path, "r", encoding='utf-8') as file:
            result_json = json.load(file)
            print(result_json)  # Add this line
    else:
        result_json = {"error": "No detection results found"}

    # Limpeza movida para depois da leitura dos resultados
    os.remove(img_path)
    logging.info(f"Limpeza concluída para {img_path}")
    print(result_img_path)  # Add this line
    print(result_json_path)  # Add this line
    return result_img, result_json
    
with gr.Blocks() as app:
    gr.Markdown("# Surya OCR and Text Line Detection via CLI")

    with gr.Tab("OCR"):
        with gr.Column():
            ocr_input_image = gr.Image(label="Input Image for OCR", type="pil")

            # Use language names for display in the dropdown
            ocr_language_selector = gr.Dropdown(
                label="Select Language for OCR",
                choices=list(language_map.keys()),  # Use language names
                value="English"
            )
            ocr_run_button = gr.Button("Run OCR")

        with gr.Column():
            ocr_output_image = gr.Image(label="OCR Output Image", type="pil", interactive=False)
            ocr_text_output = gr.TextArea(label="Recognized Text")

        ocr_run_button.click(
            fn=ocr_function_cli, inputs=[ocr_input_image, ocr_language_selector], outputs=[ocr_output_image, ocr_text_output]
        )

    with gr.Tab("Text Line Detection"):
        with gr.Column():
            detection_input_image = gr.Image(label="Input Image for Detection", type="pil")
            detection_run_button = gr.Button("Run Text Line Detection")

        with gr.Column():
            detection_output_image = gr.Image(label="Detection Output Image", type="pil", interactive=False)
            detection_json_output = gr.JSON(label="Detection JSON Output")

        detection_run_button.click(
            fn=text_line_detection_function_cli, inputs=detection_input_image, outputs=[detection_output_image, detection_json_output]
        )

if __name__ == "__main__":
    app.launch()