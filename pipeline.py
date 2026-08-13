import argparse
import logging
import os
import sys
import time

from tqdm import tqdm

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from config import LOGGING_FORMAT, LOGGING_LEVEL, LOGS_DIR
from generate_test_data import generar_datos_prueba
from src.generators.pdf_generator import run_pdf_generation
from src.processors.create_spacy_file import crear_archivo_spacy
from src.processors.create_spacy_training_data import run_create_spacy_data
from src.processors.train_spacy import entrenar_modelo_spacy

os.makedirs(LOGS_DIR, exist_ok=True)
logging.basicConfig(
    filename=os.path.join(LOGS_DIR, "pipeline_integrado.log"),
    level=getattr(logging, LOGGING_LEVEL),
    format=LOGGING_FORMAT,
    filemode="a",
)
registrador = logging.getLogger("pipeline_integrado")


def ejecutar_pipeline_integrado(numero_registros, numero_trabajadores):
    registrador.info("Iniciando pipeline: registros=%s workers=%s", numero_registros, numero_trabajadores)
    pasos = construir_pasos_pipeline(numero_registros, numero_trabajadores)
    ejecutar_pasos_pipeline(pasos)
    registrador.info("Pipeline completado exitosamente")
    print("\nPipeline integrado completado exitosamente.")


def run_integrated_pipeline(num_records, num_workers):
    ejecutar_pipeline_integrado(num_records, num_workers)


def construir_pasos_pipeline(numero_registros, numero_trabajadores):
    return [
        paso("Generar datos CSV", generar_datos_prueba, numero_registros=numero_registros),
        paso("Generar PDFs y etiquetas", run_pdf_generation, num_records=numero_registros),
        paso("Crear datos spaCy", run_create_spacy_data, num_records=numero_registros, num_workers=numero_trabajadores),
        paso("Crear archivo .spacy", crear_archivo_spacy),
        paso("Entrenar modelo spaCy", entrenar_modelo_spacy),
    ]


def paso(nombre, funcion, **argumentos):
    return {"nombre": nombre, "funcion": funcion, "argumentos": argumentos}


def ejecutar_pasos_pipeline(pasos):
    with tqdm(total=len(pasos), desc="Pipeline", unit="paso") as barra:
        for paso_actual in pasos:
            ejecutar_paso(paso_actual)
            barra.update(1)


def ejecutar_paso(paso_actual):
    registrador.info("Iniciando paso: %s", paso_actual["nombre"])
    inicio = time.time()
    try:
        paso_actual["funcion"](**paso_actual["argumentos"])
    except Exception as error:
        registrar_error_paso(paso_actual["nombre"], error)
        raise
    registrar_fin_paso(paso_actual["nombre"], inicio)


def registrar_error_paso(nombre_paso, error):
    registrador.critical("El pipeline fallo en %s: %s", nombre_paso, error, exc_info=True)
    print(f"\nERROR: fallo el paso '{nombre_paso}'. Revisa logs/pipeline_integrado.log.")


def registrar_fin_paso(nombre_paso, inicio):
    duracion = time.time() - inicio
    registrador.info("Paso '%s' completado en %.2fs", nombre_paso, duracion)


def obtener_argumentos():
    trabajadores = max(1, (os.cpu_count() or 2) // 2)
    parser = argparse.ArgumentParser(description="Orquesta el pipeline de entrenamiento documental.")
    parser.add_argument("--num_records", type=int, default=100)
    parser.add_argument("--workers", type=int, default=trabajadores)
    return parser.parse_args()


def limitar_trabajadores(numero_trabajadores):
    return min(numero_trabajadores, os.cpu_count() or 1)


if __name__ == "__main__":
    argumentos = obtener_argumentos()
    ejecutar_pipeline_integrado(argumentos.num_records, limitar_trabajadores(argumentos.workers))
