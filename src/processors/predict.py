# ==============================================================================
# SCRIPT: predict.py (Versión Final para API)
#
# PROPÓSITO:
# Este es el script de inferencia, diseñado para ser llamado por otros
# programas (como api.py). Toma un PDF, lo procesa y devuelve los datos
# extraídos en formato de diccionario Python (JSON).
#
# CAMBIOS FINALES:
# - (CRÍTICO) La función `predict_entities` ahora utiliza `return` para
#   devolver el diccionario `final_json`, en lugar de imprimirlo. Esto es
#   esencial para que la API de Flask pueda capturar el resultado.
# - Se ha limpiado la salida en la consola para que el script se enfoque en
#   retornar el valor. La lógica de guardar un archivo JSON de salida se
#   ha comentado, ya que la API se encargará de la respuesta.
# ==============================================================================

import os
import sys
import json
import logging
import argparse
import spacy
import cv2
import numpy as np
import subprocess
import tempfile
import re
from pdf2image import convert_from_path

# --- Configuración de rutas y logging ---
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))
from config import BASE_DIR, MODELS_DIR, LOGS_DIR, LOGGING_FORMAT, LOGGING_LEVEL, TESSERACT_CMD, POPPLER_PATH

# Definir rutas
MODEL_DIR = os.path.join(MODELS_DIR, 'spacy_model')
LOG_FILE = os.path.join(LOGS_DIR, 'predict.log')

# Configurar logging
logging.basicConfig(
    filename=LOG_FILE,
    level=getattr(logging, LOGGING_LEVEL),
    format=LOGGING_FORMAT,
    filemode='a'
)
logger = logging.getLogger(__name__)

def preprocess_image_for_ocr(image):
    """Limpia y pre-procesa una imagen para maximizar la precisión del OCR."""
    img_cv = np.array(image.convert('L'))
    img_cv = cv2.convertScaleAbs(img_cv, alpha=1.2, beta=0)
    _, thresh = cv2.threshold(img_cv, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    return thresh

def execute_ocr_safely(image_array, lang='spa', timeout=90):
    """Ejecuta Tesseract de forma segura usando un archivo temporal y un subproceso."""
    with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as temp_image:
        temp_path = temp_image.name
    
    try:
        cv2.imwrite(temp_path, image_array)
        
        command = [TESSERACT_CMD, temp_path, 'stdout', '-l', lang, '--psm', '6']
        
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            encoding='utf-8',
            errors='replace',
            timeout=timeout
        )

        if result.returncode != 0:
            logger.error(f"Tesseract falló con el código {result.returncode}. Error: {result.stderr}")
            raise RuntimeError(f"Tesseract error: {result.stderr}")

        return result.stdout

    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)

def predict_entities(pdf_path):
    """
    Carga el modelo spaCy entrenado, extrae entidades de un PDF y devuelve el resultado.
    """
    logger.info(f"--- Iniciando predicción para el archivo: {pdf_path} ---")

    if not os.path.exists(MODEL_DIR):
        logger.error(f"El directorio del modelo no fue encontrado en: {MODEL_DIR}")
        return {"error": "Modelo no encontrado. Ejecuta el pipeline de entrenamiento primero."}

    try:
        nlp = spacy.load(MODEL_DIR)
        logger.info("Modelo spaCy cargado exitosamente.")
    except Exception as e:
        logger.error(f"No se pudo cargar el modelo desde {MODEL_DIR}: {e}")
        return {"error": f"No se pudo cargar el modelo: {e}"}

    try:
        # 1. Conversión y OCR
        images = convert_from_path(pdf_path, dpi=200, poppler_path=POPPLER_PATH)
        image = images[0]
        processed_image = preprocess_image_for_ocr(image)
        ocr_text = execute_ocr_safely(processed_image)
        cleaned_text = re.sub(r'\s+', ' ', ocr_text).strip()
        
    except Exception as e:
        logger.error(f"Fallo en la fase de procesamiento de PDF/OCR: {e}", exc_info=True)
        return {"error": f"Fallo al procesar el PDF: {e}"}

    # 2. Predicción con el modelo
    doc = nlp(cleaned_text)
    
    # 3. Formateo de resultados
    results = {}
    for ent in doc.ents:
        if ent.label_ not in results:
            value = ent.text.strip()
            results[ent.label_] = value

    final_json = {
        "fields": {
            "alu_matricula": {"value": results.get("MATRICULA", "NO ENCONTRADO")},
            "alu_nombre": {"value": results.get("NOMBRE", "NO ENCONTRADO")},
            "alu_paterno": {"value": results.get("PATERNO", "NO ENCONTRADO")},
            "alu_materno": {"value": results.get("MATERNO", "NO ENCONTRADO")},
            "alu_carrera": {"value": results.get("CARRERA", "NO ENCONTRADO")},
            "alu_servicio": {"value": results.get("SERVICIO", "NO ENCONTRADO")}
        },
        "image_dimensions": {"width": image.width, "height": image.height}
    }
    
    logger.info(f"Predicción finalizada. Resultado: {final_json}")
    
    # --- ¡CAMBIO CRÍTICO! Se retorna el JSON para que la API lo use ---
    return final_json

if __name__ == "__main__":
    # Esta parte permite seguir usando el script desde la línea de comandos para pruebas rápidas
    parser = argparse.ArgumentParser(description="Extrae entidades de un documento PDF usando un modelo spaCy entrenado.")
    parser.add_argument("pdf_path", type=str, help="Ruta al archivo PDF a procesar.")
    args = parser.parse_args()

    if not TESSERACT_CMD or not os.path.exists(TESSERACT_CMD):
        print("Error: La ruta al ejecutable de Tesseract no está configurada correctamente en 'config.py'.")
    elif not os.path.exists(args.pdf_path):
        print(f"Error: El archivo no fue encontrado en la ruta '{args.pdf_path}'")
    else:
        try:
            # Para pruebas, el resultado se imprimirá en la consola
            prediction_result = predict_entities(args.pdf_path)
            print("\n--- JSON Final ---")
            print(json.dumps(prediction_result, indent=2, ensure_ascii=False))
        except Exception as e:
            logger.critical(f"Error fatal durante la predicción en modo script: {e}", exc_info=True)
            raise
