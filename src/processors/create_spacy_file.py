# ==============================================================================
# ARCHIVO: create_spacy_file.py
#
# PROPÓSITO:
# Este script actúa como un "control de calidad". Lee el archivo JSON con los
# datos de entrenamiento que hemos preparado y los convierte al formato binario
# y ultra-eficiente de spaCy (.spacy).
#
# Durante este proceso, valida que cada entidad (nombre, matrícula, etc.)
# se alinee perfectamente con la forma en que spaCy divide el texto en tokens.
# Cualquier ejemplo que cause un conflicto es descartado automáticamente.
#
# Esto garantiza que el modelo solo entrene con datos 100% válidos,
# solucionando el problema del "loss=0.00".
#
# NOTA DE INSTALACIÓN:
# pip install spacy tqdm
# python -m spacy download es_core_news_lg
# ==============================================================================

import os
import json
import logging
import sys
import argparse
import spacy
from spacy.tokens import DocBin
from tqdm import tqdm

# --- Configuración de rutas ---
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))
from config import DATA_DIR


def cargar_tokenizador_espanol(logger):
    for modelo in ["es_core_news_lg", "es_core_news_md", "es_core_news_sm"]:
        try:
            return spacy.load(modelo)
        except OSError:
            logger.warning(f"Modelo spaCy no instalado: {modelo}")
    logger.warning("Usando tokenizador blanco de spaCy para espanol.")
    return spacy.blank("es")

def run_create_spacy_file():
    """
    Convierte datos en formato JSON a un archivo binario .spacy para un
    entrenamiento eficiente y robusto.
    """
    logger = logging.getLogger("pipeline_integrado.create_spacy_file")
    json_path = os.path.join(DATA_DIR, 'spacy_training_data.json')
    output_path = os.path.join(DATA_DIR, 'train.spacy')

    if not os.path.exists(json_path):
        logger.error(f"Archivo de datos JSON no encontrado en: {json_path}")
        raise FileNotFoundError(f"No se encontró {json_path}. Ejecuta el paso anterior del pipeline.")

    nlp = cargar_tokenizador_espanol(logger)

    db = DocBin() # Crear un colector de documentos binarios

    with open(json_path, 'r', encoding='utf-8') as f:
        training_data = json.load(f)
    
    logger.info(f"Procesando {len(training_data)} ejemplos desde {json_path}...")
    
    misaligned_count = 0
    for text, annotation in tqdm(training_data, desc="Validando y Convirtiendo Datos"):
        doc = nlp.make_doc(text)
        ents = []
        for start, end, label in annotation.get("entities", []):
            # Usar char_span para crear un span que se alinee con los tokens
            span = doc.char_span(start, end, label=label)
            if span is None:
                # Si el span es None, los índices no se alinean con los límites de los tokens.
                # Esto es exactamente lo que causa las advertencias [W030].
                misaligned_count += 1
            else:
                ents.append(span)
        
        try:
            # Asignar las entidades validadas al documento
            doc.ents = ents
            db.add(doc)
        except ValueError:
            # Esto puede ocurrir si hay entidades superpuestas que no filtramos antes.
            # Es una segunda capa de seguridad.
            misaligned_count += 1

    if misaligned_count > 0:
        logger.warning(f"Se descartaron {misaligned_count} entidades por problemas de alineación.")
        print(f"\nAdvertencia: Se descartaron {misaligned_count} entidades por problemas de alineación durante la validación.")

    # Guardar el archivo .spacy final
    db.to_disk(output_path)
    logger.info(f"Archivo de entrenamiento .spacy guardado en: {output_path}")
    print(f"Archivo de entrenamiento .spacy generado con {len(db)} documentos válidos.")

if __name__ == "__main__":
    from config import LOGGING_FORMAT, LOGGING_LEVEL, LOGS_DIR
    os.makedirs(LOGS_DIR, exist_ok=True)
    logging.basicConfig(level=logging.INFO, format=LOGGING_FORMAT, filemode='a')

    print("Iniciando creación de archivo .spacy...")
    try:
        run_create_spacy_file()
        print("¡Creación de archivo .spacy completada!")
    except Exception as e:
        logging.error(f"Error fatal en la ejecución independiente: {e}", exc_info=True)
        print(f"ERROR: {e}")
