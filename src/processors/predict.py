import os
import sys
import json
import logging
import argparse
import torch
import re
from pdf2image import convert_from_path
import pytesseract
from transformers import LayoutLMForTokenClassification, LayoutLMTokenizerFast
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))
from config import BASE_DIR, MODELS_DIR, LOGS_DIR, TESSERACT_CMD, POPPLER_PATH, LOGGING_FORMAT, LOGGING_LEVEL

# Configurar Tesseract
pytesseract.pytesseract.tesseract_cmd = TESSERACT_CMD

# Configurar logging
os.makedirs(LOGS_DIR, exist_ok=True)
logging.basicConfig(
    filename=os.path.join(LOGS_DIR, 'predict.log'),
    level=getattr(logging, LOGGING_LEVEL),
    format=LOGGING_FORMAT
)
logger = logging.getLogger(__name__)

def normalize_text(text):
    """Normaliza texto para comparación."""
    return text.strip().lower()

def validate_prediction(field_name, value):
    """Valida la predicción según el formato esperado."""
    if field_name == 'alu_matricula' and not re.match(r'^\d{8}$', value):
        return False
    if field_name in ['alu_nombre', 'alu_paterno', 'alu_materno'] and not re.match(r'^[A-Za-z\s]+$', value):
        return False
    if field_name == 'alu_carrera':
        valid_carreras = ['Ingeniería en Sistemas', 'Ingeniería Civil', 'Administración', 'Ingeniería Industrial']
        return normalize_text(value) in [normalize_text(c) for c in valid_carreras]
    if field_name == 'alu_servicio':
        valid_servicios = ['Prácticas Profesionales', 'Servicio Social', 'Beca Académica']
        return normalize_text(value) in [normalize_text(s) for s in valid_servicios]
    return True

def preprocess_image_for_ocr(image):
    """Preprocesa la imagen para mejorar la detección de texto con OCR."""
    import cv2
    import numpy as np
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    gray = cv2.GaussianBlur(gray, (3, 3), 0)
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    gray = clahe.apply(gray)
    thresh = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
                                   cv2.THRESH_BINARY, 15, 3)
    kernel = np.ones((2, 2), np.uint8)
    return cv2.dilate(thresh, kernel, iterations=1)

def extract_text_and_bboxes(image, pdf_type='formato'):
    """Extrae texto y bboxes usando Tesseract."""
    processed_img = preprocess_image_for_ocr(image)
    custom_config = f'--oem 3 --psm {"6" if pdf_type == "formato" else "11"}'
    data = pytesseract.image_to_data(processed_img, output_type=pytesseract.Output.DICT, config=custom_config)
    
    tokens = []
    bboxes = []
    img_width, img_height = image.shape[1], image.shape[0]
    
    for i in range(len(data['text'])):
        text = data['text'][i].strip()
        if text and int(data['conf'][i]) > 75 and data['width'][i] > 5 and data['height'][i] > 5:
            x, y, w, h = data['left'][i], data['top'][i], data['width'][i], data['height'][i]
            x_min = max(0, x / img_width * 1000)
            y_min = max(0, y / img_height * 1000)
            x_max = min(1000, (x + w) / img_width * 1000)
            y_max = min(1000, (y + h) / img_height * 1000)
            if x_max > x_min and y_max > y_min:
                tokens.append(text)
                bboxes.append([int(x_min), int(y_min), int(x_max), int(y_max)])
    
    return tokens, bboxes

def predict_pdf(pdf_path, model_path, output_json):
    """Predice campos en un PDF usando LayoutLM."""
    logger.info(f"Iniciando predicción para {pdf_path}")
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    logger.info(f"Usando dispositivo: {device}")

    tokenizer = LayoutLMTokenizerFast.from_pretrained(model_path)
    model = LayoutLMForTokenClassification.from_pretrained(model_path).to(device)
    model.eval()

    labels_map = {
        0: "O",
        1: "B-ALU_MATRICULA", 2: "I-ALU_MATRICULA",
        3: "B-ALU_NOMBRE", 4: "I-ALU_NOMBRE",
        5: "B-ALU_PATERNO", 6: "I-ALU_PATERNO",
        7: "B-ALU_MATERNO", 8: "I-ALU_MATERNO",
        9: "B-ALU_CARRERA", 10: "I-ALU_CARRERA",
        11: "B-ALU_SERVICIO", 12: "I-ALU_SERVICIO"
    }

    try:
        images = convert_from_path(pdf_path, dpi=150, poppler_path=POPPLER_PATH)
        if not images:
            logger.error(f"No se pudo convertir {pdf_path} a imágenes")
            return

        predictions = {}
        pdf_type = 'formato' if 'formato' in pdf_path else 'lorem' if 'lorem' in pdf_path else 'random'
        for i, img in enumerate(images):
            import numpy as np
            img_np = np.array(img)
            tokens, bboxes = extract_text_and_bboxes(img_np, pdf_type)
            logger.info(f"Página {i+1}: {len(tokens)} tokens extraídos")

            if not tokens:
                logger.warning(f"No se extrajeron tokens en página {i+1}")
                continue

            encoding = tokenizer(
                tokens,
                is_split_into_words=True,
                return_tensors="pt",
                truncation=True,
                padding="max_length",
                max_length=512,
                return_offsets_mapping=True
            )

            word_ids = encoding.word_ids()
            aligned_bboxes = [[0, 0, 1000, 1000]] * 512
            for j, word_id in enumerate(word_ids):
                if word_id is not None and word_id < len(bboxes):
                    aligned_bboxes[j] = bboxes[word_id]

            input_ids = encoding["input_ids"].to(device)
            attention_mask = encoding["attention_mask"].to(device)
            bbox_tensor = torch.tensor([aligned_bboxes], dtype=torch.long).to(device)

            with torch.no_grad():
                outputs = model(input_ids=input_ids, attention_mask=attention_mask, bbox=bbox_tensor)
                logits = outputs.logits
                preds = torch.argmax(logits, dim=2).cpu().numpy()[0]

            field_values = {
                "alu_matricula": "", "alu_nombre": "", "alu_paterno": "",
                "alu_materno": "", "alu_carrera": "", "alu_servicio": ""
            }
            current_field = None
            current_value = []

            for j, pred in enumerate(preds):
                label = labels_map.get(pred, "O")
                token = tokens[word_ids[j]] if word_ids[j] is not None else ""
                if label.startswith("B-"):
                    if current_field and current_value:
                        value = " ".join(current_value)
                        if validate_prediction(current_field.lower(), value):
                            field_values[current_field.lower()] = value
                    current_field = label[2:]
                    current_value = [token] if token else []
                elif label.startswith("I-") and current_field == label[2:]:
                    if token:
                        current_value.append(token)
                else:
                    if current_field and current_value:
                        value = " ".join(current_value)
                        if validate_prediction(current_field.lower(), value):
                            field_values[current_field.lower()] = value
                    current_field = None
                    current_value = []
            
            if current_field and current_value:
                value = " ".join(current_value)
                if validate_prediction(current_field.lower(), value):
                    field_values[current_field.lower()] = value

            predictions[f"page_{i+1}"] = field_values
            logger.info(f"Predicciones página {i+1}: {field_values}")

        output_path = os.path.join(BASE_DIR, output_json)
        if os.path.exists(output_path):
            os.remove(output_path)  # Borrar archivo existente
            logger.info(f"Archivo existente {output_path} eliminado")
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(predictions, f, ensure_ascii=False, indent=2)
        logger.info(f"Predicciones guardadas en {output_path}")
        print(f"Predicciones guardadas en {output_path}")

    except Exception as e:
        logger.error(f"Error en predicción: {str(e)}")
        raise

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Predice campos en un PDF usando LayoutLM")
    parser.add_argument("--pdf_path", required=True, help="Ruta al PDF")
    parser.add_argument("--output_json", default="output.json", help="Archivo JSON de salida")
    args = parser.parse_args()

    model_path = os.path.join(MODELS_DIR, "layoutlm_model_best")
    predict_pdf(args.pdf_path, model_path, args.output_json)