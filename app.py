import gradio as gr
from PIL import Image
import io
from surya.ocr import run_ocr
from surya.model.detection.model import load_model as load_det_model, load_processor as load_det_processor
from surya.model.recognition.model import load_model as load_rec_model
from surya.model.recognition.processor import load_processor as load_rec_processor

# Load models and processors
det_processor, det_model = load_det_processor(), load_det_model()
rec_model, rec_processor = load_rec_model(), load_rec_processor()

def perform_ocr(image, language):
    # Convert gradio image to PIL Image
    if image is not None:
        image = Image.fromarray(image)
    else:
        return "No image uploaded"

    # Perform OCR
    langs = [language]  # You can expand this to support multiple languages
    predictions = run_ocr([image], [langs], det_model, det_processor, rec_model, rec_processor)

    # Extract text from predictions
    result = ""
    for page in predictions[0]:  # Assuming single image input
        for line in page['text_lines']:
            result += line['text'] + "\n"

    return result

# Define the Gradio interface
iface = gr.Interface(
    fn=perform_ocr,
    inputs=[
        gr.Image(type="numpy", label="Upload an image"),
        gr.Dropdown(choices=["en", "fr", "de", "es", "it"], label="Select language", value="en")
    ],
    outputs=gr.Textbox(label="Extracted Text"),
    title="OCR with Surya",
    description="Upload an image to extract text using Optical Character Recognition."
)

# Launch the app
iface.launch()
