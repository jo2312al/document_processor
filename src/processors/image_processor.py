# ==============================================================================
# ARCHIVO: image_processor.py (Versión 8 - con Parámetros Corregidos)
#
# PROPÓSITO:
# Utiliza la librería profesional 'albumentations' para aplicar un conjunto
# de aumentos de datos de alta fidelidad, simulando los defectos de una foto
# tomada con la cámara de un teléfono.
#
# CAMBIOS (v8):
# - (CRÍTICO) Se han actualizado todos los nombres de los parámetros en el
#   pipeline de 'albumentations' para que sean compatibles con las versiones
#   más recientes de la librería y se eliminen las advertencias.
# ==============================================================================

import os
import shutil
import random
import cv2
import numpy as np
from pdf2image import convert_from_path
import logging
import sys
import argparse
from PIL import Image
from tqdm import tqdm
import albumentations as A

# --- Configuración de rutas ---
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))
from config import BASE_DIR, GENERATED_DOCS_DIR, GENERATED_IMAGES_DIR, POPPLER_PATH

# --- Pipeline de Aumento de Datos con Parámetros Corregidos ---
TRANSFORM_PIPELINE = A.Compose([
    # --- ¡CORRECCIÓN! Se usan los nombres de parámetro modernos ---
    A.Perspective(scale=(0.02, 0.08), p=0.7, pad_val=(255, 255, 255)),
    A.ElasticTransform(alpha=1, sigma=50, p=0.3),
    A.OpticalDistortion(distort_limit=0.1, p=0.4),
    A.MotionBlur(blur_limit=7, p=0.5),
    A.GaussianBlur(blur_limit=(3, 7), p=0.4),
    A.GaussNoise(p=0.5), # var_limit ya no es necesario
    A.RandomShadow(p=0.3),
    A.ImageCompression(quality_lower=40, quality_upper=90, p=0.8),
    A.RandomBrightnessContrast(brightness_limit=0.2, contrast_limit=0.2, p=0.7),
])

def process_single_pdf(pdf_path, output_dir):
    """
    Convierte un PDF a imagen y le aplica el pipeline de aumentos.
    """
    logger = logging.getLogger("pipeline_integrado.image_processor")
    try:
        images = convert_from_path(pdf_path, dpi=random.randint(150, 250), poppler_path=POPPLER_PATH)
        base_name = os.path.splitext(os.path.basename(pdf_path))[0]
        
        for i, image_pil in enumerate(images):
            image_cv = cv2.cvtColor(np.array(image_pil), cv2.COLOR_RGB2BGR)
            
            transformed = TRANSFORM_PIPELINE(image=image_cv)
            transformed_image = transformed['image']
            
            output_path = os.path.join(output_dir, f"{base_name}_page_{i+1}.jpg")
            cv2.imwrite(output_path, transformed_image)

    except Exception as e:
        logger.error(f"Fallo al procesar {pdf_path}: {e}")

# --- Función Principal (Lógica Encapsulada) ---
def run_image_processing(num_records):
    """
    Función principal que procesa los PDFs a imágenes. Ahora es importable.
    """
    logger = logging.getLogger("pipeline_integrado.image_processor")
    
    if os.path.exists(GENERATED_IMAGES_DIR):
        shutil.rmtree(GENERATED_IMAGES_DIR)
    os.makedirs(GENERATED_IMAGES_DIR, exist_ok=True)
    logger.info(f"Directorio de imágenes de salida limpio y listo: {GENERATED_IMAGES_DIR}")

    pdf_files_all = [f for f in os.listdir(GENERATED_DOCS_DIR) if f.lower().endswith('.pdf')]
    if not pdf_files_all:
        logger.warning(f"No se encontraron PDFs en {GENERATED_DOCS_DIR}")
        return

    if num_records < len(pdf_files_all):
        pdf_files_to_process = random.sample(pdf_files_all, num_records)
    else:
        pdf_files_to_process = pdf_files_all
    
    logger.info(f"Iniciando procesamiento de {len(pdf_files_to_process)} PDFs a imágenes...")
    
    # Bucle secuencial con barra de progreso para máxima estabilidad
    for pdf_file in tqdm(pdf_files_to_process, desc="Procesando PDFs a Imágenes"):
        pdf_path = os.path.join(GENERATED_DOCS_DIR, pdf_file)
        process_single_pdf(pdf_path, GENERATED_IMAGES_DIR)

# --- Bloque de Ejecución Independiente ---
if __name__ == "__main__":
    from config import LOGGING_FORMAT, LOGGING_LEVEL, LOGS_DIR
    os.makedirs(LOGS_DIR, exist_ok=True)
    logging.basicConfig(level=logging.INFO, format=LOGGING_FORMAT, filemode='a')
    
    parser = argparse.ArgumentParser(description="Procesa PDFs a imágenes con aumento de datos avanzado.")
    parser.add_argument("--num_records", type=int, default=50, help="Número de PDFs a procesar.")
    args = parser.parse_args()
    
    print(f"Procesando {args.num_records} PDFs a imágenes...")
    try:
        run_image_processing(args.num_records)
        print("¡Procesamiento de imágenes completado!")
    except Exception as e:
        logging.error(f"Error fatal en la ejecución independiente: {e}", exc_info=True)
        print(f"ERROR: {e}")
