import gradio as gr
import json
import subprocess
from PIL import Image
import os
import tempfile
import logging

# Configuração básica de logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def save_temp_image(img):
    temp_dir = tempfile.mkdtemp()
    img_path = os.path.join(temp_dir, "input_image.png")
    img.save(img_path)
    logging.info(f"Imagem salva em {img_path}")
    return img_path, temp_dir

def run_command(command):
    try:
        result = subprocess.check_output(command, shell=True, stderr=subprocess.STDOUT, encoding='utf-8')
        logging.info("Command Output: " + result)
        return result
    except subprocess.CalledProcessError as e:
        logging.error(f"Command failed with error: {e.output}")
        return None

def ocr_function_cli(img, lang_name):
    img_path, temp_dir = save_temp_image(img)
    command = f"surya_ocr {img_path} --langs {lang_name} --images --results_dir {temp_dir}"
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
    else:
        result_json = {"error": "No detection results found"}

    # Limpeza movida para depois da leitura dos resultados
    os.remove(img_path)
    logging.info(f"Limpeza concluída para {img_path}")
    return result_img, result_json
    
with gr.Blocks() as app:
    gr.Markdown("# Surya OCR and Text Line Detection via CLI")

    with gr.Tab("OCR"):
        with gr.Column():
            ocr_input_image = gr.Image(label="Input Image for OCR", type="pil")
            ocr_language_selector = gr.Dropdown(
                label="Select Language for OCR",
                choices=[
                    "Afrikaans",
                    "Amharic",
                    "Arabic",
                    "Assamese",
                    "Azerbaijani",
                    "Belarusian",
                    "Bulgarian",
                    "Bengali",
                    "Breton",
                    "Bosnian",
                    "Catalan",
                    "Czech",
                    "Welsh",
                    "Danish",
                    "German",
                    "Greek",
                    "English",
                    "Esperanto",
                    "Spanish",
                    "Estonian",
                    "Basque",
                    "Persian",
                    "Finnish",
                    "French",
                    "Western Frisian",
                    "Irish",
                    "Scottish Gaelic",
                    "Galician",
                    "Gujarati",
                    "Hausa",
                    "Hebrew",
                    "Hindi",
                    "Croatian",
                    "Hungarian",
                    "Armenian",
                    "Indonesian",
                    "Icelandic",
                    "Italian",
                    "Japanese",
                    "Javanese",
                    "Georgian",
                    "Kazakh",
                    "Khmer",
                    "Kannada",
                    "Korean",
                    "Kurdish",
                    "Kyrgyz",
                    "Latin",
                    "Lao",
                    "Lithuanian",
                    "Latvian",
                    "Malagasy",
                    "Macedonian",
                    "Malayalam",
                    "Mongolian",
                    "Marathi",
                    "Malay",
                    "Burmese",
                    "Nepali",
                    "Dutch",
                    "Norwegian",
                    "Oromo",
                    "Oriya",
                    "Punjabi",
                    "Polish",
                    "Pashto",
                    "Portuguese",
                    "Romanian",
                    "Russian",
                    "Sanskrit",
                    "Sindhi",
                    "Sinhala",
                    "Slovak",
                    "Slovenian",
                    "Somali",
                    "Albanian",
                    "Serbian",
                    "Sundanese",
                    "Swedish",
                    "Swahili",
                    "Tamil",
                    "Telugu",
                    "Thai",
                    "Tagalog",
                    "Turkish",
                    "Uyghur",
                    "Ukrainian",
                    "Urdu",
                    "Uzbek",
                    "Vietnamese",
                    "Xhosa",
                    "Yiddish",
                    "Chinese"
                ],
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