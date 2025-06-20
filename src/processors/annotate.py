import os
import sys
import json
import re
import logging
from pdf2image import convert_from_path
import pytesseract
import cv2
import numpy as np
from fuzzywuzzy import fuzz
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))
from config import BASE_DIR, CONVERTED_PDFS_DIR, LABELS_DIR, YOLO_DIR, LOGS_DIR, TESSERACT_CMD, POPPLER_PATH, LOGGING_FORMAT, LOGGING_LEVEL
import multiprocessing as mp
from multiprocessing import Manager

# Configurar Tesseract
pytesseract.pytesseract.tesseract_cmd = TESSERACT_CMD

# Configurar logging en el proceso principal
os.makedirs(LOGS_DIR, exist_ok=True)
logging.basicConfig(
    filename=os.path.join(LOGS_DIR, 'annotate.log'),
    level=getattr(logging, LOGGING_LEVEL),
    format=LOGGING_FORMAT,
    filemode='w'
)
logger = logging.getLogger(__name__)
logger.info("Logging configurado correctamente")

def convert_to_yolo_bbox(bbox, img_width, img_height):
    """Convierte bbox [x, y, width, height] a formato YOLO [x_center, y_center, width, height] normalizado."""
    x, y, w, h = bbox
    if w < 5 or h < 5:
        logger.warning(f"Bbox inválido descartado: {bbox} (w={w}, h={h})")
        return None
    x_center = (x + w / 2) / img_width
    y_center = (y + h / 2) / img_height
    w_norm = w / img_width
    h_norm = h / img_height
    return x_center, y_center, w_norm, h_norm

def preprocess_image_for_ocr(image):
    """Preprocesa la imagen para mejorar la detección de texto con OCR."""
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    gray = cv2.GaussianBlur(gray, (3, 3), 0)
    thresh = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
                                   cv2.THRESH_BINARY, 15, 3)
    kernel = np.ones((2, 2), np.uint8)
    return cv2.dilate(thresh, kernel, iterations=1)

def preprocess_matricula_region(image, region):
    """Preprocesa específicamente la región de la matrícula."""
    gray = cv2.cvtColor(region, cv2.COLOR_BGR2GRAY)
    gray = cv2.convertScaleAbs(gray, alpha=1.5, beta=0)
    thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)[1]
    kernel = np.ones((2, 2), np.uint8)
    return cv2.dilate(thresh, kernel, iterations=2)

def detect_text_bboxes(image):
    """Detecta texto en la imagen usando Tesseract con preprocesamiento y filtrado."""
    try:
        processed_img = preprocess_image_for_ocr(image)
        custom_config = r'--oem 3 --psm 11'
        data = pytesseract.image_to_data(processed_img, output_type=pytesseract.Output.DICT, config=custom_config)
        
        bboxes = []
        for i in range(len(data['text'])):
            if data['text'][i].strip() and int(data['conf'][i]) > 40 and data['width'][i] > 5 and data['height'][i] > 5:
                x, y, w, h = data['left'][i], data['top'][i], data['width'][i], data['height'][i]
                text = data['text'][i].strip()
                bboxes.append({'text': text, 'bbox': [x, y, w, h]})
        logger.info(f"Detectados {len(bboxes)} textos en la imagen")
        return bboxes
    except Exception as e:
        logger.error(f"Error en detección de texto: {str(e)}")
        return []

def normalize_text(text):
    """Normaliza texto para comparación."""
    return re.sub(r'\s+', ' ', text.lower().strip())

def process_single_pdf(pdf_file, pdf_dir, label_dir, output_dir, poppler_path, class_map, stats):
    """Procesa un solo PDF y genera anotaciones YOLO."""
    # Configurar logging por proceso
    process_logger = logging.getLogger(f"{__name__}.{pdf_file}")
    process_logger.setLevel(getattr(logging, LOGGING_LEVEL))
    process_handler = logging.FileHandler(os.path.join(LOGS_DIR, 'annotate.log'), mode='a')
    process_handler.setFormatter(logging.Formatter(LOGGING_FORMAT))
    process_logger.addHandler(process_handler)

    try:
        base_name = pdf_file.replace('.pdf', '').rsplit('_page_', 1)[0]
        json_file = f"labels_{base_name}.json"
        json_path = os.path.join(label_dir, json_file)
        
        if not os.path.exists(json_path):
            process_logger.error(f"No se encontró JSON para {pdf_file}: {json_path}")
            return
        
        with open(json_path, 'r', encoding='utf-8') as f:
            label_data = json.load(f)
        process_logger.info(f"Cargado JSON: {json_path}")
        
        pdf_path = os.path.join(pdf_dir, pdf_file)
        images = convert_from_path(pdf_path, dpi=150, poppler_path=poppler_path)
        if not images:
            process_logger.error(f"No se pudo convertir {pdf_file} a imágenes")
            return
        
        for i, img in enumerate(images):
            img_np = np.array(img)
            img_width, img_height = img_np.shape[1], img_np.shape[0]
            process_logger.info(f"Procesando página {i+1} de {pdf_file}: {img_width}x{img_height}")
            
            # Guardar dimensiones en JSON
            label_data['image_dimensions'] = {'width': img_width, 'height': img_height}
            with open(json_path, 'w', encoding='utf-8') as f:
                json.dump(label_data, f, ensure_ascii=False, indent=2)
            
            # Preprocesar región de matrícula
            matricula_region = img_np[0:int(img_height*0.1), 0:int(img_width*0.3)]
            matricula_processed = preprocess_matricula_region(img_np, matricula_region) if matricula_region.size else img_np
            
            text_bboxes = detect_text_bboxes(img_np)
            process_logger.info(f"Detectados {len(text_bboxes)} textos en página {i+1} de {pdf_file}")
            
            yolo_file = os.path.join(output_dir, f"{base_name}_page_{i+1}.txt")
            with open(yolo_file, 'w') as f:
                for field_name, field_data in label_data.get('fields', {}).items():
                    value = field_data.get('value', '').strip()
                    if not value:
                        process_logger.warning(f"Valor vacío para {field_name} en {json_path}")
                        continue
                    
                    stats[field_name]['attempts'] += 1
                    class_id = class_map.get(field_name)
                    if class_id is None:
                        process_logger.warning(f"Etiqueta desconocida en {json_path}: {field_name}")
                        continue
                    
                    found = False
                    for text_bbox in text_bboxes:
                        detected_text = text_bbox['text']
                        similarity = fuzz.partial_ratio(normalize_text(value), normalize_text(detected_text))
                        if similarity >= 60:
                            bbox = text_bbox['bbox']
                            yolo_bbox = convert_to_yolo_bbox(bbox, img_width, img_height)
                            if yolo_bbox:
                                x_center, y_center, w_norm, h_norm = yolo_bbox
                                f.write(f"{class_id} {x_center:.6f} {y_center:.6f} {w_norm:.6f} {h_norm:.6f}\n")
                                process_logger.info(f"Anotado {field_name}={value} (sim={similarity}%) en {yolo_file}")
                                stats[field_name]['successes'] += 1
                                found = True
                                break
                    
                    if not found:
                        process_logger.warning(f"No se encontró {value} para {field_name} en {yolo_file} (sim<60%)")
            
            process_logger.info(f"Anotación generada: {yolo_file}")
    
    except Exception as e:
        process_logger.error(f"Error procesando {pdf_file}: {str(e)}")
    finally:
        process_handler.close()

def annotate_pdfs():
    """Genera anotaciones YOLO usando PDFs y OCR con fuzzy matching en paralelo."""
    logger.info("Iniciando anotación de PDFs")
    
    pdf_dir = CONVERTED_PDFS_DIR
    label_dir = LABELS_DIR
    output_dir = YOLO_DIR
    os.makedirs(output_dir, exist_ok=True)
    logger.info(f"Directorio de salida para anotaciones: {output_dir}")
    
    pdf_files = [f for f in os.listdir(pdf_dir) if f.endswith('.pdf')]
    logger.info(f"Encontrados {len(pdf_files)} PDFs en {pdf_dir}: {pdf_files[:5]}...")
    
    if not pdf_files:
        logger.warning(f"No se encontraron PDFs en {pdf_dir}")
        print(f"Advertencia: No se encontraron PDFs en {pdf_dir}")
        return

    class_map = {
        'alu_matricula': 0,
        'alu_nombre': 1,
        'alu_paterno': 2,
        'alu_materno': 3,
        'alu_carrera': 4,
        'alu_servicio': 5
    }

    # Inicializar stats como Manager dict para compartir entre procesos
    manager = Manager()
    stats = manager.dict({field: {'attempts': 0, 'successes': 0} for field in class_map.keys()})

    poppler_path = POPPLER_PATH if os.path.exists(POPPLER_PATH) else None

    # Limitar número de procesos en Windows
    num_processes = min(mp.cpu_count(), 4)  # Reducido para estabilidad en Windows
    with mp.Pool(processes=num_processes) as pool:
        pool.starmap(process_single_pdf, [
            (pdf_file, pdf_dir, label_dir, output_dir, poppler_path, class_map, stats)
            for pdf_file in pdf_files
        ])

    # Imprimir resumen
    print("\nResumen de detección:")
    for field, count in stats.items():
        total = count['attempts']
        found = count['successes']
        percentage = (found / total * 100) if total > 0 else 0
        print(f"{found} de {total} {field}s encontrados ({percentage:.2f}%)")
        logger.info(f"{found} de {total} {field}s encontrados ({percentage:.2f}%)")

    logger.info("Anotación finalizada")
    print("Anotación finalizada")

if __name__ == "__main__":
    # Asegurar que el código principal solo se ejecute en el proceso principal
    mp.set_start_method('spawn', force=True)  # Forzar 'spawn' en Windows
    try:
        annotate_pdfs()
    except KeyboardInterrupt:
        logger.info("Interrupción por teclado, finalizando ejecución")
        print("Interrupción por teclado, finalizando ejecución")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Error en la ejecución principal: {str(e)}")
        print(f"Error en la ejecución principal: {str(e)}")
        sys.exit(1)