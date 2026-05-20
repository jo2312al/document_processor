# ==============================================================================
# ARCHIVO: train_spacy.py (Versión Profesional - Definitiva)
#
# PROPÓSITO:
# Entrenar el modelo de la forma más robusta, rápida y recomendada por spaCy,
# asegurando que se ejecuten todas las épocas de entrenamiento.
#
# CAMBIOS:
# - Se ha reemplazado el bucle de entrenamiento manual por la función
#   `spacy.cli.train`, que es el estándar de la industria.
# - Se genera un archivo de configuración `config.cfg` explícito con todos
#   los parámetros necesarios (incluyendo `max_epochs`), lo que soluciona
#   el problema de que el entrenamiento se detenga prematuramente.
# ==============================================================================

import os
import logging
import sys
import spacy
from spacy.cli.train import train as spacy_train
from spacy.cli.init_config import init_config

# --- Configuración de rutas ---
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))
from config import DATA_DIR, MODELS_DIR, BASE_DIR

def run_training():
    """
    Entrena o re-entrena un modelo NER de spaCy usando un archivo .spacy y un config.cfg
    generado explícitamente para asegurar un entrenamiento completo.
    """
    logger = logging.getLogger("pipeline_integrado.train_spacy")
    
    # Rutas
    training_data_path = os.path.join(DATA_DIR, 'train.spacy')
    dev_data_path = os.path.join(DATA_DIR, 'train.spacy') # Usamos los mismos datos para validación
    final_model_path = os.path.join(MODELS_DIR, 'spacy_model')
    config_path = os.path.join(BASE_DIR, "config.cfg")

    if not os.path.exists(training_data_path):
        logger.error(f"No se encontró el archivo de entrenamiento: {training_data_path}")
        raise FileNotFoundError(f"Ejecuta 'create_spacy_file.py' primero.")

    # --- Creación del Archivo de Configuración Explícito ---
    logger.info("Generando archivo de configuración explícito (config.cfg)...")
    
    # 1. Generar la configuración base en memoria
    # Usamos 'efficiency' para un entrenamiento más rápido en CPU
    config = init_config(
        lang="es",
        pipeline=["tok2vec", "ner"],
        optimize="efficiency" 
    )

    # 2. Modificar la configuración con nuestros parámetros deseados
    config["paths"]["train"] = training_data_path
    config["paths"]["dev"] = dev_data_path
    config["paths"]["vectors"] = "es_core_news_md" # Usar el modelo mediano, más rápido
    config["training"]["max_epochs"] = 15  # ¡CRÍTICO! Forzar las 15 épocas
    config["training"]["patience"] = 16    # Paciencia > max_epochs para asegurar que no se detenga
    
    # 3. Guardar la configuración final y completa en el disco
    config.to_disk(config_path)
    logger.info(f"Archivo config.cfg guardado en: {config_path}")

    logger.info("Iniciando entrenamiento con spacy.cli.train...")
    print("\nIniciando entrenamiento del modelo (método profesional)...")

    # 4. Llamar a la función de entrenamiento de spaCy
    spacy_train(
        config_path,
        output_path=final_model_path,
    )
    
    logger.info(f"Modelo final guardado en: {final_model_path}")
    print(f"\n¡Entrenamiento completado! Modelo guardado en: {final_model_path}")


if __name__ == "__main__":
    from config import LOGGING_FORMAT, LOGGING_LEVEL, LOGS_DIR
    os.makedirs(LOGS_DIR, exist_ok=True)
    logging.basicConfig(level=logging.INFO, format=LOGGING_FORMAT, filemode='a')

    try:
        run_training()
    except Exception as e:
        logging.error(f"Error fatal durante el entrenamiento: {e}", exc_info=True)
        print(f"ERROR: {e}")
