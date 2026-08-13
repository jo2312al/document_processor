import logging
import os
import sys

from spacy.cli.init_config import init_config
from spacy.cli.train import train as entrenar_spacy_cli

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from config import BASE_DIR, DATA_DIR, LOGGING_FORMAT, MODELS_DIR


def entrenar_modelo_spacy():
    registrador = logging.getLogger("pipeline.entrenar_modelo_spacy")
    rutas = construir_rutas_entrenamiento()
    validar_datos_entrenamiento(rutas["entrenamiento"])
    configuracion = crear_configuracion_spacy(rutas)
    guardar_configuracion(configuracion, rutas["configuracion"], registrador)
    ejecutar_entrenamiento(rutas, registrador)


def run_training():
    entrenar_modelo_spacy()


def construir_rutas_entrenamiento():
    return {
        "entrenamiento": os.path.join(DATA_DIR, "train.spacy"),
        "validacion": os.path.join(DATA_DIR, "train.spacy"),
        "modelo_final": os.path.join(MODELS_DIR, "spacy_model"),
        "configuracion": os.path.join(BASE_DIR, "config.cfg"),
    }


def validar_datos_entrenamiento(ruta_entrenamiento):
    if not os.path.exists(ruta_entrenamiento):
        raise FileNotFoundError("Ejecuta create_spacy_file.py primero.")


def crear_configuracion_spacy(rutas):
    configuracion = init_config(lang="es", pipeline=["tok2vec", "ner"], optimize="efficiency")
    configuracion["paths"]["train"] = rutas["entrenamiento"]
    configuracion["paths"]["dev"] = rutas["validacion"]
    configuracion["paths"]["vectors"] = None
    configuracion["training"]["max_epochs"] = 15
    configuracion["training"]["patience"] = 16
    return configuracion


def guardar_configuracion(configuracion, ruta_configuracion, registrador):
    configuracion.to_disk(ruta_configuracion)
    registrador.info("Archivo config.cfg guardado en: %s", ruta_configuracion)


def ejecutar_entrenamiento(rutas, registrador):
    print("\nIniciando entrenamiento del modelo spaCy...")
    entrenar_spacy_cli(rutas["configuracion"], output_path=rutas["modelo_final"])
    registrador.info("Modelo final guardado en: %s", rutas["modelo_final"])
    print(f"\nEntrenamiento completado. Modelo guardado en: {rutas['modelo_final']}")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format=LOGGING_FORMAT)
    entrenar_modelo_spacy()
