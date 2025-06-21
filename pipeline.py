import os
import sys
import subprocess
import argparse
import logging
import time
import multiprocessing as mp
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from config import BASE_DIR, LOGS_DIR, LOGGING_FORMAT, LOGGING_LEVEL

# Configurar logging
os.makedirs(LOGS_DIR, exist_ok=True)
logging.basicConfig(
    filename=os.path.join(LOGS_DIR, 'pipeline.log'),
    level=getattr(logging, LOGGING_LEVEL),
    format=LOGGING_FORMAT,
    filemode='w'
)
logger = logging.getLogger(__name__)
logger.info("Logging configurado para pipeline")

def run_script(script_path, args=None):
    """Ejecuta un script Python con argumentos opcionales."""
    cmd = [sys.executable, script_path]
    if args:
        cmd.extend(args)
    try:
        start_time = time.time()
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        elapsed_time = time.time() - start_time
        logger.info(f"Ejecutado {script_path} en {elapsed_time:.2f}s")
        logger.debug(f"Salida: {result.stdout}")
        print(f"Ejecutado {script_path} en {elapsed_time:.2f}s")
        return elapsed_time
    except subprocess.CalledProcessError as e:
        logger.error(f"Error ejecutando {script_path}: {e.stderr}")
        print(f"Error ejecutando {script_path}: {e.stderr}")
        raise

def run_pipeline(num_pdfs):
    """Ejecuta el pipeline completo con multiprocessing."""
    logger.info(f"Iniciando pipeline con {num_pdfs} PDFs")
    print(f"Iniciando pipeline con {num_pdfs} PDFs")
    total_time = 0.0

    scripts = [
        ("generate_names_surnames.py", ["--num_records", str(num_pdfs * 2)]),
        ("generate_test_data.py", ["--num_records", str(num_pdfs)]),
        ("src/generators/pdf_generator.py", ["--num_pdfs", str(num_pdfs), "--type", "formato", "lorem", "random", "--dist", "0.4", "0.3", "0.3"]),
        ("src/processors/image_processor.py", ["--num_pdfs", str(num_pdfs)]),
        ("src/processors/image_to_pdf_converter.py", ["--num_images", str(num_pdfs)]),
        ("src/processors/annotate.py", []),
        ("src/processors/generate_annotations.py", []),
        ("src/processors/train.py", []),
    ]

    for script_path, args in scripts:
        full_path = os.path.join(BASE_DIR, script_path)
        if not os.path.exists(full_path):
            logger.error(f"Script no encontrado: {full_path}")
            print(f"Error: Script no encontrado: {full_path}")
            sys.exit(1)
        elapsed_time = run_script(full_path, args)
        total_time += elapsed_time

    logger.info(f"Pipeline completado en {total_time:.2f}s")
    print(f"Pipeline completado en {total_time:.2f}s")
    return total_time

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Ejecuta el pipeline de procesamiento de PDFs.")
    parser.add_argument("--num_pdfs", type=int, default=15, help="Número de PDFs a procesar")
    args = parser.parse_args()

    try:
        mp.set_start_method('spawn', force=True)
        run_pipeline(args.num_pdfs)
    except Exception as e:
        logger.error(f"Error en pipeline: {str(e)}")
        print(f"Error en pipeline: {str(e)}")
        sys.exit(1)