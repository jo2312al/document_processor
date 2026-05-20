# ==============================================================================
# ARCHIVO 1 (CORREGIDO): pipeline_integrado.py
# UBICACIÓN: En la raíz de tu proyecto
#
# CAMBIOS:
# - (CRÍTICO) Se ha añadido el argumento 'num_workers' a la llamada de la
#   función 'run_create_spacy_data' para solucionar el TypeError.
# ==============================================================================

import os
import sys
import logging
import time
import argparse
from tqdm import tqdm

# --- Configuración de rutas y logging ---
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))
from config import (
    BASE_DIR, LOGS_DIR, LOGGING_FORMAT, LOGGING_LEVEL, MODELS_DIR,
    DATA_DIR, GENERATED_DOCS_DIR, GENERATED_IMAGES_DIR
)

# --- Importar la lógica refactorizada de cada script ---
from generate_test_data import generate_test_data
from src.generators.pdf_generator import run_pdf_generation
from src.processors.image_processor import run_image_processing
from src.processors.create_spacy_training_data import run_create_spacy_data
from src.processors.create_spacy_file import run_create_spacy_file
from src.processors.train_spacy import run_training

# Configurar logging para el pipeline
os.makedirs(LOGS_DIR, exist_ok=True)
logging.basicConfig(
    filename=os.path.join(LOGS_DIR, 'pipeline_integrado.log'),
    level=getattr(logging, LOGGING_LEVEL),
    format='%(asctime)s - %(levelname)s - %(message)s',
    filemode='a'
)
pipeline_logger = logging.getLogger("pipeline_integrado")

def run_integrated_pipeline(num_records, num_workers):
    """
    Ejecuta el pipeline completo de forma integrada.
    """
    pipeline_logger.info(f"================ INICIANDO PIPELINE (records={num_records}, workers={num_workers}) ================")
    
    # Lista de pasos a ejecutar
    pipeline_steps = [
        {"name": "1. Generando Datos de Prueba (CSV)", "func": generate_test_data, "kwargs": {"num_records": num_records}},
        {"name": "2. Generando PDFs y Etiquetas", "func": run_pdf_generation, "kwargs": {"num_records": num_records}},
        {"name": "3. Procesando PDFs a Imágenes", "func": run_image_processing, "kwargs": {"num_records": num_records}},
        # --- ¡CORRECCIÓN! Se añade 'num_workers' a los argumentos ---
        {"name": "4. Creando Datos JSON para spaCy", "func": run_create_spacy_data, "kwargs": {"num_records": num_records, "num_workers": num_workers}},
        {"name": "5. Validando y Creando Archivo .spacy", "func": run_create_spacy_file, "kwargs": {}},
        {"name": "6. Entrenando Modelo spaCy", "func": run_training, "kwargs": {}}
    ]

    with tqdm(total=len(pipeline_steps), desc="Pipeline General", unit="paso") as pbar:
        for step in pipeline_steps:
            pbar.set_description(f"Paso: {step['name']}")
            pipeline_logger.info(f"--- Iniciando paso: {step['name']} ---")
            start_time = time.time()
            
            try:
                step_kwargs = step.get('kwargs', {})
                step['func'](**step_kwargs)
                elapsed_time = time.time() - start_time
                pipeline_logger.info(f"--- Paso '{step['name']}' completado en {elapsed_time:.2f}s ---")
            except Exception as e:
                pipeline_logger.critical(f"El pipeline falló en '{step['name']}': {e}", exc_info=True)
                print(f"\nERROR: El pipeline falló en el paso '{step['name']}'. Revisa el log 'pipeline_integrado.log'.")
                return
            
            pbar.update(1)

    pipeline_logger.info("================ PIPELINE COMPLETADO EXITOSAMENTE ================")
    print("\n¡Pipeline integrado completado exitosamente!")

if __name__ == "__main__":
    half_cores = max(1, (os.cpu_count() or 2) // 2)
    parser = argparse.ArgumentParser(description="Orquesta el pipeline integrado para entrenar el modelo de extracción.")
    parser.add_argument("--num_records", type=int, default=100, help="Número de documentos a generar y procesar.")
    parser.add_argument("--workers", type=int, default=half_cores, help=f"Workers para procesos paralelos (defecto: {half_cores}).")
    args = parser.parse_args()
    
    max_workers = os.cpu_count() or 1
    if args.workers > max_workers:
        args.workers = max_workers

    run_integrated_pipeline(args.num_records, args.workers)
