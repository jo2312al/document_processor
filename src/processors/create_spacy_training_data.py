# ==============================================================================
# ARCHIVO: create_spacy_training_data.py (Versión 12 - Adaptado para NOMBRE_COMPLETO)
#
# PROPÓSITO:
# Combina la lógica de 'image_processor.py' y 'create_spacy_training_data.py'
# en un único script paralelo para una velocidad máxima.
#
# CAMBIOS (v12):
# - (ADAPTACIÓN) La lógica de etiquetado ahora es flexible. Lee la clave
#   directamente del archivo de etiquetas JSON (ej. "NOMBRE_COMPLETO")
#   y la usa como la etiqueta de la entidad para spaCy.
# ==============================================================================

import os
import json
import logging
import sys
import argparse
import re
import random
import cv2
import numpy as np
from PIL import Image
import pytesseract
from thefuzz import fuzz
from pdf2image import convert_from_path
from concurrent.futures import ProcessPoolExecutor, as_completed
from tqdm import tqdm
import albumentations as A

# --- Configuración de rutas y logging ---
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))
try:
    from config import BASE_DIR, DATA_DIR, LOGS_DIR, GENERATED_DOCS_DIR, LABELS_DIR, TESSERACT_CMD, POPPLER_PATH
except ImportError:
    # Definir rutas por defecto si config.py no está disponible
    BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
    DATA_DIR = os.path.join(BASE_DIR, "data")
    LOGS_DIR = os.path.join(BASE_DIR, "logs")
    GENERATED_DOCS_DIR = os.path.join(BASE_DIR, "generated_docs")
    LABELS_DIR = os.path.join(BASE_DIR, "labels")
    TESSERACT_CMD = None # O la ruta a tu ejecutable de Tesseract
    POPPLER_PATH = None  # O la ruta a tu carpeta bin de Poppler

# Configurar Tesseract
if TESSERACT_CMD and os.path.exists(TESSERACT_CMD):
    pytesseract.pytesseract.tesseract_cmd = TESSERACT_CMD

# Pipeline de Aumento de Datos Optimizado
TRANSFORM_PIPELINE = A.Compose([
    A.Perspective(scale=(0.02, 0.08), p=0.7, pad_val=(255, 255, 255)),
    A.MotionBlur(blur_limit=5, p=0.5),
    A.GaussianBlur(blur_limit=(3, 5), p=0.5),
    A.GaussNoise(p=0.4),
    A.ImageCompression(quality_lower=50, quality_upper=95, p=0.7),
    A.RandomBrightnessContrast(brightness_limit=0.2, contrast_limit=0.2, p=0.7),
])

def find_best_fuzzy_match(ocr_text, value, score_cutoff=85):
    """Encuentra la mejor coincidencia difusa usando un enfoque de palabras."""
    if not value or not ocr_text: return None
    value_words = value.split()
    if not value_words: return None
    ocr_words_with_indices = [(m.group(0), m.start()) for m in re.finditer(r'\S+', ocr_text)]
    if not ocr_words_with_indices or len(ocr_words_with_indices) < len(value_words): return None
    
    ocr_words = [item[0] for item in ocr_words_with_indices]
    best_score, best_match_indices = 0, None

    for i in range(len(ocr_words) - len(value_words) + 1):
        ocr_phrase = " ".join(ocr_words[i : i + len(value_words)])
        score = fuzz.ratio(value.lower(), ocr_phrase.lower())
        if score > best_score:
            best_score = score
            start_char = ocr_words_with_indices[i][1]
            last_word_info = ocr_words_with_indices[i + len(value_words) - 1]
            end_char = last_word_info[1] + len(last_word_info[0])
            best_match_indices = (start_char, end_char)

    if best_score >= score_cutoff:
        return (best_match_indices[0], best_match_indices[1], best_score)
    return None

def process_pdf_to_spacy_data(pdf_file, ground_truth):
    """
    Función de worker que realiza el ciclo completo: PDF -> Imagen -> Aumento -> OCR -> Alineación.
    """
    if not ground_truth: return None
    
    pdf_path = os.path.join(GENERATED_DOCS_DIR, pdf_file)
    try:
        # 1. PDF a Imagen
        image_pil = convert_from_path(pdf_path, dpi=200, poppler_path=POPPLER_PATH, first_page=1, last_page=1)[0]
        
        # 2. Aumento de Datos
        image_cv = cv2.cvtColor(np.array(image_pil), cv2.COLOR_RGB2BGR)
        transformed_image = TRANSFORM_PIPELINE(image=image_cv)['image']
        
        # 3. OCR
        ocr_text = pytesseract.image_to_string(transformed_image, lang='spa', config='--psm 6')
        
        # 4. Alineación de Entidades
        potential_entities = []
        for key, data in ground_truth.items():
            value = data.get('value', '').strip()
            if not value: continue
            
            match_info = find_best_fuzzy_match(ocr_text, value)
            if match_info:
                start, end, score = match_info
                
                # --- CAMBIO CLAVE ---
                # Se usa la clave del JSON ("NOMBRE_COMPLETO", "alu_matricula", etc.) como la etiqueta.
                # Se convierte a mayúsculas para seguir la convención de spaCy.
                label = key.upper()
                
                potential_entities.append({"start": start, "end": end, "label": label, "score": score})

        if not potential_entities: return None

        # Lógica para resolver solapamientos (la entidad con mayor 'score' gana)
        potential_entities.sort(key=lambda x: x['score'], reverse=True)
        final_entities = []
        accepted_spans = []
        for entity in potential_entities:
            is_overlapping = any(max(entity['start'], s) < min(entity['end'], e) for s, e in accepted_spans)
            if not is_overlapping:
                final_entities.append((entity['start'], entity['end'], entity['label']))
                accepted_spans.append((entity['start'], entity['end']))

        if not final_entities: return None
            
        return (ocr_text, {"entities": final_entities})
    except Exception as e:
        # Loguear el error específico para ayudar a depurar
        logging.getLogger("worker").error(f"Fallo en el worker para {pdf_file}: {e}", exc_info=False)
        return None

def run_create_spacy_data(num_records, num_workers):
    """Orquesta la creación del archivo de datos para spaCy."""
    logger = logging.getLogger("pipeline.create_spacy_data")
    output_file = os.path.join(DATA_DIR, 'spacy_training_data.json')

    logger.info(f"Pre-cargando etiquetas desde {LABELS_DIR}...")
    # Carga las etiquetas del JSON en memoria para un acceso rápido
    labels_data = {
        label_file.replace('labels_', '').replace('.json', ''): json.load(open(os.path.join(LABELS_DIR, label_file), 'r', encoding='utf-8'))['fields']
        for label_file in os.listdir(LABELS_DIR) if label_file.endswith('.json')
    }
    logger.info(f"Cargadas {len(labels_data)} etiquetas en memoria.")

    pdf_files_all = [f for f in os.listdir(GENERATED_DOCS_DIR) if f.lower().endswith('.pdf')]
    if not pdf_files_all:
        logger.error(f"No se encontraron PDFs en {GENERATED_DOCS_DIR}. Ejecuta 'pdf_generator' primero.")
        return
        
    # Selecciona una muestra aleatoria si se especifica un número menor al total
    if num_records < len(pdf_files_all):
        pdf_files_to_process = random.sample(pdf_files_all, num_records)
    else:
        pdf_files_to_process = pdf_files_all
        
    logger.info(f"Procesando {len(pdf_files_to_process)} PDFs en paralelo con {num_workers} workers...")
    
    training_data = []
    # Usa un pool de procesos para paralelizar el trabajo pesado
    with ProcessPoolExecutor(max_workers=num_workers) as executor:
        futures = {}
        for pdf_file in pdf_files_to_process:
            base_name = os.path.splitext(pdf_file)[0]
            ground_truth = labels_data.get(base_name)
            if ground_truth:
                future = executor.submit(process_pdf_to_spacy_data, pdf_file, ground_truth)
                futures[future] = pdf_file
        
        # Recolecta los resultados a medida que se completan
        for future in tqdm(as_completed(futures), total=len(futures), desc="Procesando y Alineando Documentos"):
            result = future.result()
            if result:
                training_data.append(result)

    lost_count = len(pdf_files_to_process) - len(training_data)
    logger.warning(f"Proceso completado. {lost_count} de {len(pdf_files_to_process)} documentos no pudieron ser procesados.")
    print(f"\nProceso completado. {lost_count} de {len(pdf_files_to_process)} documentos no pudieron ser procesados.")

    if not training_data:
        logger.error("No se pudo generar ningún dato de entrenamiento válido.")
        return
        
    # Guarda el resultado final en un único archivo JSON
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(training_data, f, ensure_ascii=False, indent=4)
        
    logger.info(f"Proceso finalizado. Se generaron {len(training_data)} ejemplos válidos.")
    print(f"Archivo 'spacy_training_data.json' generado con {len(training_data)} ejemplos.")

if __name__ == "__main__":
    os.makedirs(LOGS_DIR, exist_ok=True)
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', filemode='a')
    
    half_cores = max(1, (os.cpu_count() or 2) // 2)
    parser = argparse.ArgumentParser(description="Genera datos de entrenamiento para spaCy a partir de PDFs.")
    parser.add_argument("--num_records", type=int, default=50, help="Número de PDFs a procesar.")
    parser.add_argument("--workers", type=int, default=half_cores, help=f"Número de procesos paralelos (defecto: {half_cores}).")
    args = parser.parse_args()
    
    max_workers = os.cpu_count() or 1
    if args.workers > max_workers:
        args.workers = max_workers

    print(f"Generando datos de entrenamiento para {args.num_records} PDFs usando {args.workers} workers...")
    try:
        run_create_spacy_data(args.num_records, args.workers)
        print("¡Creación de datos de entrenamiento completada!")
    except Exception as e:
        logging.error(f"Error fatal en la ejecución independiente: {e}", exc_info=True)
        print(f"ERROR: {e}")