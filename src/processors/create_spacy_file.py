import argparse
import json
import logging
import os
import sys

import spacy
from spacy.tokens import DocBin
from tqdm import tqdm

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from config import DATA_DIR, LOGGING_FORMAT


def cargar_tokenizador_espanol(registrador):
    for modelo in ["es_core_news_lg", "es_core_news_md", "es_core_news_sm"]:
        tokenizador = intentar_cargar_modelo(modelo, registrador)
        if tokenizador:
            return tokenizador
    registrador.warning("Usando tokenizador blanco de spaCy para espanol.")
    return spacy.blank("es")


def crear_archivo_spacy():
    registrador = logging.getLogger("pipeline.crear_archivo_spacy")
    ruta_json = os.path.join(DATA_DIR, "spacy_training_data.json")
    ruta_salida = os.path.join(DATA_DIR, "train.spacy")
    validar_archivo_json(ruta_json)
    datos_entrenamiento = cargar_datos_entrenamiento(ruta_json)
    base_documentos, descartadas = convertir_datos(datos_entrenamiento, registrador)
    guardar_base_documentos(base_documentos, ruta_salida)
    mostrar_resumen(base_documentos, descartadas, ruta_salida, registrador)


def run_create_spacy_file():
    crear_archivo_spacy()


def intentar_cargar_modelo(nombre_modelo, registrador):
    try:
        return spacy.load(nombre_modelo)
    except OSError:
        registrador.warning("Modelo spaCy no instalado: %s", nombre_modelo)
        return None


def validar_archivo_json(ruta_json):
    if not os.path.exists(ruta_json):
        raise FileNotFoundError(f"No se encontro {ruta_json}. Ejecuta el paso anterior del pipeline.")


def cargar_datos_entrenamiento(ruta_json):
    with open(ruta_json, "r", encoding="utf-8") as archivo:
        return json.load(archivo)


def convertir_datos(datos_entrenamiento, registrador):
    tokenizador = cargar_tokenizador_espanol(registrador)
    base_documentos = DocBin()
    descartadas = 0
    for texto, anotacion in tqdm(datos_entrenamiento, desc="Validando datos"):
        descartadas += agregar_documento(tokenizador, base_documentos, texto, anotacion)
    return base_documentos, descartadas


def agregar_documento(tokenizador, base_documentos, texto, anotacion):
    documento = tokenizador.make_doc(texto)
    entidades, descartadas = crear_entidades(documento, anotacion)
    try:
        documento.ents = entidades
        base_documentos.add(documento)
    except ValueError:
        descartadas += 1
    return descartadas


def crear_entidades(documento, anotacion):
    entidades = []
    descartadas = 0
    for inicio, fin, etiqueta in anotacion.get("entities", []):
        entidad = documento.char_span(inicio, fin, label=etiqueta)
        if entidad is None:
            descartadas += 1
        else:
            entidades.append(entidad)
    return entidades, descartadas


def guardar_base_documentos(base_documentos, ruta_salida):
    base_documentos.to_disk(ruta_salida)


def mostrar_resumen(base_documentos, descartadas, ruta_salida, registrador):
    if descartadas:
        registrador.warning("Entidades descartadas por alineacion: %s", descartadas)
        print(f"Advertencia: {descartadas} entidades descartadas por alineacion.")
    registrador.info("Archivo .spacy guardado en: %s", ruta_salida)
    print(f"Archivo train.spacy generado con {len(base_documentos)} documentos validos.")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format=LOGGING_FORMAT)
    crear_archivo_spacy()
