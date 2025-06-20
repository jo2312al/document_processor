import os
import sys
import json
import logging
import pytesseract
import cv2
import numpy as np
from pdf2image import convert_from_path
from transformers import LayoutLMForTokenClassification, AutoTokenizer
import torch
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))
from config import BASE_DIR, LOGS_DIR, TESSERACT_CMD, POPPLER_PATH, LOGGING_FORMAT, LOGGING_LEVEL

# Configurar Tesseract
pytesseract.pytesseract.tesseract_cmd = TESSERACT_CMD

# Configurar logging
os.makedirs(LOGS_DIR, exist_ok=True)
logging.basicConfig(
    filename=os.path.join(LOGS_DIR, 'predict.log'),
    level=getattr(logging, LOGGING_LEVEL),
    format=LOGGING_FORMAT,
    filemode='w'
)
logger = logging.getLogger(__name__)
logger.info("Logging configurado para predicción")

def preprocess_image_for_ocr(image):
    """Preprocesa la imagen para mejorar la detección de texto con OCR."""
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    gray = cv2.GaussianBlur(gray, (3, 3), 0)
    thresh = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
                                   cv2.THRESH_BINARY, 15, 3)
    kernel = np.ones((2, 2), np.uint8)
    return cv2.dilate(thresh, kernel, iterations=1)

def extract_text_and_bboxes(pdf_path, poppler_path=None):
    """Extrae texto y bboxes de un PDF usando Tesseract."""
    try:
        images = convert_from_path(pdf_path, dpi=150, poppler_path=poppler_path)
        img = np.array(images[0])  # Primera página
        img_width, img_height = img.shape[1], img.shape[0]
        
        processed_img = preprocess_image_for_ocr(img)
        custom_config = r'--oem 3 --psm 11'
        data = pytesseract.image_to_data(processed_img, output_type=pytesseract.Output.DICT, config=custom_config)
        
        words, bboxes = [], []
        for i in range(len(data['text'])):
            if data['text'][i].strip() and int(data['conf'][i]) > 60 and data['width'][i] > 5 and data['height'][i] > 5:
                words.append(data['text'][i])
                x, y, w, h = data['left'][i], data['top'][i], data['width'][i], data['height'][i]
                # Normalizar bboxes para LayoutLM (0-1000)
                bboxes.append([
                    int(1000 * x / img_width),
                    int(1000 * y / img_height),
                    int(1000 * (x + w) / img_width),
                    int(1000 * (y + h) / img_height)
                ])
        logger.info(f"Extraídos {len(words)} tokens de {pdf_path}")
        logger.debug(f"Primeros 5 tokens: {words[:5]}")
        logger.debug(f"Primeros 5 bboxes: {bboxes[:5]}")
        return words, bboxes, img_width, img_height
    except Exception as e:
        logger.error(f"Error extrayendo texto de {pdf_path}: {str(e)}")
        return [], [], 0, 0

def predict_with_layoutlm(pdf_path, model_path, poppler_path=None):
    """Procesa un PDF y devuelve un JSON con los datos extraídos."""
    # Cargar modelo y tokenizer
    try:
        tokenizer = AutoTokenizer.from_pretrained(model_path, use_fast=False)
        model = LayoutLMForTokenClassification.from_pretrained(model_path)
        model.eval()
        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        model.to(device)
        logger.info(f"Modelo cargado desde {model_path}, usando dispositivo: {device}")
    except Exception as e:
        logger.error(f"Error cargando modelo: {str(e)}")
        return {}

    # Extraer texto y bboxes
    words, bboxes, img_width, img_height = extract_text_and_bboxes(pdf_path, poppler_path)
    if not words:
        logger.warning(f"No se extrajeron tokens de {pdf_path}")
        return {}

    # Filtrar tokens irrelevantes (e.g., encabezados)
    filtered_words, filtered_bboxes = [], []
    for word, bbox in zip(words, bboxes):
        if not any(keyword in word.lower() for keyword in ["tecnologico", "departamento", "oficio", "asunto", "constancia"]):
            filtered_words.append(word)
            filtered_bboxes.append(bbox)
    words, bboxes = filtered_words, filtered_bboxes
    logger.info(f"Filtrados a {len(words)} tokens relevantes")

    # Tokenizar
    try:
        encoding = tokenizer(
            words,
            boxes=bboxes,
            return_tensors="pt",
            padding=True,
            truncation=True,
            max_length=512
        )
        input_ids = encoding['input_ids'].to(device)
        attention_mask = encoding['attention_mask'].to(device)
        bbox = encoding.get('bbox', [[0, 0, 0, 0]] * len(words))
        if isinstance(bbox, list):
            bbox = torch.tensor([bbox[:input_ids.shape[1]]], dtype=torch.long).to(device)
        logger.debug(f"Dimensiones - input_ids: {input_ids.shape}, attention_mask: {attention_mask.shape}, bbox: {bbox.shape}")
    except Exception as e:
        logger.error(f"Error tokenizando datos: {str(e)}")
        return {}

    # Predecir
    try:
        with torch.no_grad():
            outputs = model(input_ids=input_ids, attention_mask=attention_mask, bbox=bbox)
        logits = outputs.logits
        predictions = torch.argmax(logits, dim=2)[0]  # Primera instancia
    except Exception as e:
        logger.error(f"Error en predicción: {str(e)}")
        return {}

    # Mapear etiquetas
    label_map = {
        0: "alu_matricula",
        1: "alu_nombre",
        2: "alu_paterno",
        3: "alu_materno",
        4: "alu_carrera",
        5: "alu_servicio"
    }

    # Estructurar resultados
    result = {field: "" for field in label_map.values()}
    for i, (word, pred) in enumerate(zip(words[:len(predictions)-2], predictions[1:-1])):  # Ajustar longitud
        if pred.item() in label_map:
            field = label_map[pred.item()]
            result[field] += word + " "
    result = {k: v.strip() for k, v in result.items() if v.strip()}
    
    logger.info(f"Predicciones para {pdf_path}: {result}")
    return result

def main(pdf_path, output_json_path):
    """Procesa un PDF y guarda los resultados en un JSON."""
    model_path = os.path.join(BASE_DIR, "models", "layoutlm_model")
    poppler_path = POPPLER_PATH if os.path.exists(POPPLER_PATH) else None
    
    result = predict_with_layoutlm(pdf_path, model_path, poppler_path)
    if result:
        with open(output_json_path, 'w', encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        logger.info(f"Resultados guardados en {output_json_path}")
    else:
        logger.error(f"No se generaron resultados para {pdf_path}")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Extraer datos de un PDF usando LayoutLM")
    parser.add_argument("--pdf_path", required=True, help="Ruta al PDF de entrada")
    parser.add_argument("--output_json", default="output.json", help="Ruta al JSON de salida")
    args = parser.parse_args()
    
    try:
        main(args.pdf_path, args.output_json)
    except Exception as e:
        logger.error(f"Error en ejecución principal: {str(e)}")
        sys.exit(1)