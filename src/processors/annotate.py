import os
import sys
import json
import cv2
import numpy as np
import pytesseract
from pdf2image import convert_from_path
from fuzzywuzzy import fuzz
from concurrent.futures import ProcessPoolExecutor
import re
import logging
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))
from config import CONVERTED_PDFS_DIR, LABELS_DIR, YOLO_DIR, TESSERACT_CMD, POPPLER_PATH, LOGS_DIR, LOGGING_FORMAT, LOGGING_LEVEL

# Configurar Tesseract
pytesseract.pytesseract.tesseract_cmd = TESSERACT_CMD

# Configurar logging
os.makedirs(LOGS_DIR, exist_ok=True)
logging.basicConfig(
    filename=os.path.join(LOGS_DIR, 'annotate.log'),
    level=getattr(logging, LOGGING_LEVEL),
    format=LOGGING_FORMAT
)
logger = logging.getLogger(__name__)

def normalize_text(text):
    """Normaliza texto para comparación."""
    return text.strip().lower()

def validate_field(field_name, text):
    """Valida el formato del campo."""
    if field_name == 'alu_matricula':
        return bool(re.match(r'^\d{8}$', text))
    elif field_name in ['alu_nombre', 'alu_paterno', 'alu_materno']:
        return bool(re.match(r'^[A-Za-z\s]+$', text))
    elif field_name == 'alu_carrera':
        valid_carreras = ['Ingeniería en Sistemas', 'Ingeniería Civil', 'Administración', 'Ingeniería Industrial']
        return normalize_text(text) in [normalize_text(c) for c in valid_carreras]
    elif field_name == 'alu_servicio':
        valid_servicios = ['Prácticas Profesionales', 'Servicio Social', 'Beca Académica']
        return normalize_text(text) in [normalize_text(s) for s in valid_servicios]
    return False

def preprocess_image_for_ocr(image):
    """Preprocesa la imagen para mejorar la detección de texto con OCR."""
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    gray = cv2.GaussianBlur(gray, (3, 3), 0)
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    gray = clahe.apply(gray)
    thresh = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 15, 3)
    kernel = np.ones((2, 2), np.uint8)
    return cv2.dilate(thresh, kernel, iterations=1)

def convert_to_yolo_bbox(bbox, img_width, img_height):
    """Convierte bbox [x, y, w, h] a formato YOLO [x_center, y_center, w_norm, h_norm]."""
    x, y, w, h = bbox
    if w <= 5 or h <= 5:
        return None
    x_center = (x + w / 2) / img_width
    y_center = (y + h / 2) / img_height
    w_norm = w / img_width
    h_norm = h / img_height
    return [x_center, y_center, w_norm, h_norm]

def detect_text_bboxes(image, pdf_type):
    """Detecta texto en la imagen usando Tesseract con PSM dinámico."""
    processed_img = preprocess_image_for_ocr(image)
    psm = '6' if pdf_type == 'formato' else '11'
    custom_config = f'--oem 3 --psm {psm}'
    data = pytesseract.image_to_data(processed_img, output_type=pytesseract.Output.DICT, config=custom_config)
    
    bboxes = []
    for i in range(len(data['text'])):
        text = data['text'][i].strip()
        if text and int(data['conf'][i]) > 75 and data['width'][i] > 5 and data['height'][i] > 5:
            x, y, w, h = data['left'][i], data['top'][i], data['width'][i], data['height'][i]
            bboxes.append({'text': text, 'bbox': [x, y, w, h]})
    return bboxes

def process_single_pdf(args):
    """Procesa un solo PDF para generar anotaciones YOLO."""
    pdf_file, pdf_dir, label_dir, output_dir, poppler_path, class_map, stats = args
    pdf_path = os.path.join(pdf_dir, pdf_file)
    base_name = pdf_file.replace('.pdf', '')
    pdf_type = 'formato' if 'formato' in base_name else 'lorem' if 'lorem' in base_name else 'random'
    json_file = os.path.join(label_dir, f"labels_{base_name}.json")
    yolo_file = os.path.join(output_dir, f"{base_name}_page_1.txt")
    
    if not os.path.exists(json_file):
        logger.warning(f"No se encontró JSON correspondiente para {pdf_file}: {json_file}")
        return
    
    try:
        with open(json_file, 'r', encoding='utf-8') as f:
            label_data = json.load(f)
        
        images = convert_from_path(pdf_path, dpi=150, poppler_path=poppler_path)
        if not images:
            logger.warning(f"No se pudo convertir {pdf_file} a imágenes")
            return
        
        img = np.array(images[0])
        img_width, img_height = img.shape[1], img.shape[0]
        text_bboxes = detect_text_bboxes(img, pdf_type)
        
        if os.path.exists(yolo_file):
            os.remove(yolo_file)
            logger.info(f"Archivo existente {yolo_file} eliminado")
        
        with open(yolo_file, 'w', encoding='utf-8') as f:
            for field_name, field_data in label_data.get('fields', {}).items():
                value = field_data.get('value', '').strip()
                if not value:
                    logger.warning(f"Valor vacío para {field_name} en {json_file}")
                    continue
                found = False
                for text_bbox in text_bboxes:
                    detected_text = text_bbox['text']
                    similarity = fuzz.partial_ratio(normalize_text(value), normalize_text(detected_text))
                    if similarity >= 80 and validate_field(field_name, detected_text):
                        bbox = text_bbox['bbox']
                        yolo_bbox = convert_to_yolo_bbox(bbox, img_width, img_height)
                        if yolo_bbox:
                            class_id = list(class_map.keys())[list(class_map.values()).index(f'B-{field_name.upper()}')]
                            f.write(f"{class_id} {yolo_bbox[0]:.6f} {yolo_bbox[1]:.6f} {yolo_bbox[2]:.6f} {yolo_bbox[3]:.6f}\n")
                            found = True
                            stats[field_name]['successes'] += 1
                            break
                if not found:
                    stats[field_name]['failures'] += 1
                    logger.warning(f"No se encontró coincidencia para {field_name} en {pdf_file}")
    
    except Exception as e:
        logger.error(f"Error procesando {pdf_file}: {str(e)}")

def annotate_pdfs():
    """Procesa todos los PDFs en CONVERTED_PDFS_DIR y genera estadísticas."""
    logger.info("Iniciando anotación de PDFs")
    os.makedirs(YOLO_DIR, exist_ok=True)
    
    class_map = {
        0: 'B-ALU_MATRICULA', 1: 'B-ALU_NOMBRE', 2: 'B-ALU_PATERNO',
        3: 'B-ALU_MATERNO', 4: 'B-ALU_CARRERA', 5: 'B-ALU_SERVICIO'
    }
    stats = {
        field: {'successes': 0, 'failures': 0}
        for field in ['alu_matricula', 'alu_nombre', 'alu_paterno', 'alu_materno', 'alu_carrera', 'alu_servicio']
    }
    
    pdf_files = [f for f in os.listdir(CONVERTED_PDFS_DIR) if f.endswith('.pdf')]
    if not pdf_files:
        logger.warning(f"No se encontraron PDFs en {CONVERTED_PDFS_DIR}")
        print(f"No se encontraron PDFs en {CONVERTED_PDFS_DIR}")
        return
    
    with ProcessPoolExecutor(max_workers=4) as executor:
        executor.map(process_single_pdf, [(pdf_file, CONVERTED_PDFS_DIR, LABELS_DIR, YOLO_DIR, POPPLER_PATH, class_map, stats) for pdf_file in pdf_files])
    
    for field, counts in stats.items():
        logger.info(f"Campo {field}: {counts['successes']} éxitos, {counts['failures']} fallos")
    print(f"Estadísticas de anotación: {stats}")

if __name__ == "__main__":
    try:
        annotate_pdfs()
    except Exception as e:
        logger.error(f"Error en la ejecución principal: {str(e)}")
        print(f"Error en la ejecución principal: {str(e)}")