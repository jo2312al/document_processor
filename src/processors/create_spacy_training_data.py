import argparse
import json
import logging
import os
import random
import re
import sys
from concurrent.futures import ProcessPoolExecutor, as_completed

import albumentations as A
import cv2
import numpy as np
import pytesseract
from pdf2image import convert_from_path
from thefuzz import fuzz
from tqdm import tqdm

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

try:
    from config import DATA_DIR, GENERATED_DOCS_DIR, LABELS_DIR, LOGS_DIR, POPPLER_PATH, TESSERACT_CMD
except ImportError:
    BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    DATA_DIR = os.path.join(BASE_DIR, "data")
    GENERATED_DOCS_DIR = os.path.join(BASE_DIR, "generated_docs")
    LABELS_DIR = os.path.join(BASE_DIR, "labels")
    LOGS_DIR = os.path.join(BASE_DIR, "logs")
    POPPLER_PATH = None
    TESSERACT_CMD = None

if TESSERACT_CMD and os.path.exists(TESSERACT_CMD):
    pytesseract.pytesseract.tesseract_cmd = TESSERACT_CMD

AUMENTO_IMAGEN = A.Compose([
    A.Perspective(scale=(0.02, 0.08), p=0.7, pad_val=(255, 255, 255)),
    A.MotionBlur(blur_limit=5, p=0.5),
    A.GaussianBlur(blur_limit=(3, 5), p=0.5),
    A.GaussNoise(p=0.4),
    A.ImageCompression(quality_lower=50, quality_upper=95, p=0.7),
    A.RandomBrightnessContrast(brightness_limit=0.2, contrast_limit=0.2, p=0.7),
])


def encontrar_mejor_coincidencia(texto_ocr, valor, puntaje_minimo=85):
    if not valor or not texto_ocr:
        return None
    palabras_valor = valor.split()
    palabras_ocr = obtener_palabras_con_indices(texto_ocr)
    if len(palabras_ocr) < len(palabras_valor):
        return None
    return buscar_ventana_similar(palabras_ocr, palabras_valor, valor, puntaje_minimo)


def find_best_fuzzy_match(ocr_text, value, score_cutoff=85):
    return encontrar_mejor_coincidencia(ocr_text, value, score_cutoff)


def procesar_pdf_para_spacy(nombre_pdf, valores_reales):
    if not valores_reales:
        return None
    try:
        texto_ocr = extraer_texto_aumentado(nombre_pdf)
        entidades = alinear_entidades(texto_ocr, valores_reales)
        if not entidades:
            return None
        return texto_ocr, {"entities": entidades}
    except Exception as error:
        logging.getLogger("worker").error("Fallo worker %s: %s", nombre_pdf, error)
        return None


def process_pdf_to_spacy_data(pdf_file, ground_truth):
    return procesar_pdf_para_spacy(pdf_file, ground_truth)


def crear_datos_spacy(numero_registros, numero_trabajadores):
    registrador = logging.getLogger("pipeline.crear_datos_spacy")
    etiquetas = cargar_etiquetas(registrador)
    archivos_pdf = seleccionar_pdfs(numero_registros, registrador)
    datos_entrenamiento = procesar_pdfs_en_paralelo(archivos_pdf, etiquetas, numero_trabajadores)
    guardar_datos_entrenamiento(datos_entrenamiento, archivos_pdf, registrador)


def run_create_spacy_data(num_records, num_workers):
    crear_datos_spacy(num_records, num_workers)


def obtener_palabras_con_indices(texto):
    return [(coincidencia.group(0), coincidencia.start()) for coincidencia in re.finditer(r"\S+", texto)]


def buscar_ventana_similar(palabras_ocr, palabras_valor, valor, puntaje_minimo):
    mejor = None
    for indice in range(len(palabras_ocr) - len(palabras_valor) + 1):
        candidato = evaluar_ventana(palabras_ocr, palabras_valor, valor, indice)
        if mejor is None or candidato[2] > mejor[2]:
            mejor = candidato
    return mejor if mejor and mejor[2] >= puntaje_minimo else None


def evaluar_ventana(palabras_ocr, palabras_valor, valor, indice):
    frase = " ".join(palabra for palabra, _ in palabras_ocr[indice: indice + len(palabras_valor)])
    puntaje = fuzz.ratio(valor.lower(), frase.lower())
    inicio = palabras_ocr[indice][1]
    ultima_palabra, ultimo_inicio = palabras_ocr[indice + len(palabras_valor) - 1]
    return inicio, ultimo_inicio + len(ultima_palabra), puntaje


def extraer_texto_aumentado(nombre_pdf):
    ruta_pdf = os.path.join(GENERATED_DOCS_DIR, nombre_pdf)
    imagen = convertir_primera_pagina(ruta_pdf)
    imagen_aumentada = AUMENTO_IMAGEN(image=imagen)["image"]
    return pytesseract.image_to_string(imagen_aumentada, lang="spa", config="--psm 6")


def convertir_primera_pagina(ruta_pdf):
    pagina = convert_from_path(ruta_pdf, dpi=200, poppler_path=POPPLER_PATH, first_page=1, last_page=1)[0]
    return cv2.cvtColor(np.array(pagina), cv2.COLOR_RGB2BGR)


def alinear_entidades(texto_ocr, valores_reales):
    candidatas = crear_entidades_candidatas(texto_ocr, valores_reales)
    return resolver_solapamientos(candidatas)


def crear_entidades_candidatas(texto_ocr, valores_reales):
    entidades = []
    for clave, datos in valores_reales.items():
        entidad = crear_entidad_candidata(texto_ocr, clave, datos)
        if entidad:
            entidades.append(entidad)
    return entidades


def crear_entidad_candidata(texto_ocr, clave, datos):
    valor = datos.get("value", "").strip()
    coincidencia = encontrar_mejor_coincidencia(texto_ocr, valor)
    if not coincidencia:
        return None
    inicio, fin, puntaje = coincidencia
    return {"inicio": inicio, "fin": fin, "etiqueta": clave.upper(), "puntaje": puntaje}


def resolver_solapamientos(entidades):
    resultado = []
    rangos_aceptados = []
    for entidad in sorted(entidades, key=lambda item: item["puntaje"], reverse=True):
        if not tiene_solapamiento(entidad, rangos_aceptados):
            resultado.append((entidad["inicio"], entidad["fin"], entidad["etiqueta"]))
            rangos_aceptados.append((entidad["inicio"], entidad["fin"]))
    return resultado


def tiene_solapamiento(entidad, rangos_aceptados):
    return any(max(entidad["inicio"], inicio) < min(entidad["fin"], fin) for inicio, fin in rangos_aceptados)


def cargar_etiquetas(registrador):
    registrador.info("Cargando etiquetas desde %s", LABELS_DIR)
    return {clave_etiqueta(nombre): leer_etiqueta(nombre) for nombre in os.listdir(LABELS_DIR) if nombre.endswith(".json")}


def clave_etiqueta(nombre_archivo):
    return nombre_archivo.replace("labels_", "").replace(".json", "")


def leer_etiqueta(nombre_archivo):
    ruta = os.path.join(LABELS_DIR, nombre_archivo)
    with open(ruta, "r", encoding="utf-8") as archivo:
        return json.load(archivo)["fields"]


def seleccionar_pdfs(numero_registros, registrador):
    archivos = [nombre for nombre in os.listdir(GENERATED_DOCS_DIR) if nombre.lower().endswith(".pdf")]
    if not archivos:
        registrador.error("No se encontraron PDFs en %s", GENERATED_DOCS_DIR)
        return []
    return random.sample(archivos, numero_registros) if numero_registros < len(archivos) else archivos


def procesar_pdfs_en_paralelo(archivos_pdf, etiquetas, numero_trabajadores):
    datos_entrenamiento = []
    with ProcessPoolExecutor(max_workers=numero_trabajadores) as ejecutor:
        futuros = crear_futuros(ejecutor, archivos_pdf, etiquetas)
        for futuro in tqdm(as_completed(futuros), total=len(futuros), desc="Alineando documentos"):
            agregar_resultado(datos_entrenamiento, futuro.result())
    return datos_entrenamiento


def crear_futuros(ejecutor, archivos_pdf, etiquetas):
    futuros = {}
    for nombre_pdf in archivos_pdf:
        valores_reales = etiquetas.get(os.path.splitext(nombre_pdf)[0])
        if valores_reales:
            futuros[ejecutor.submit(procesar_pdf_para_spacy, nombre_pdf, valores_reales)] = nombre_pdf
    return futuros


def agregar_resultado(datos_entrenamiento, resultado):
    if resultado:
        datos_entrenamiento.append(resultado)


def guardar_datos_entrenamiento(datos_entrenamiento, archivos_pdf, registrador):
    perdidos = len(archivos_pdf) - len(datos_entrenamiento)
    registrador.warning("Documentos no procesados: %s de %s", perdidos, len(archivos_pdf))
    print(f"\nProceso completado. {perdidos} de {len(archivos_pdf)} documentos no pudieron procesarse.")
    if datos_entrenamiento:
        escribir_json_entrenamiento(datos_entrenamiento, registrador)


def escribir_json_entrenamiento(datos_entrenamiento, registrador):
    ruta_salida = os.path.join(DATA_DIR, "spacy_training_data.json")
    with open(ruta_salida, "w", encoding="utf-8") as archivo:
        json.dump(datos_entrenamiento, archivo, ensure_ascii=False, indent=4)
    registrador.info("Ejemplos validos generados: %s", len(datos_entrenamiento))
    print(f"Archivo spacy_training_data.json generado con {len(datos_entrenamiento)} ejemplos.")


def obtener_argumentos():
    trabajadores = max(1, (os.cpu_count() or 2) // 2)
    parser = argparse.ArgumentParser(description="Genera datos de entrenamiento para spaCy.")
    parser.add_argument("--num_records", type=int, default=50)
    parser.add_argument("--workers", type=int, default=trabajadores)
    return parser.parse_args()


def limitar_trabajadores(numero_trabajadores):
    return min(numero_trabajadores, os.cpu_count() or 1)


if __name__ == "__main__":
    os.makedirs(LOGS_DIR, exist_ok=True)
    logging.basicConfig(level=logging.INFO)
    argumentos = obtener_argumentos()
    crear_datos_spacy(argumentos.num_records, limitar_trabajadores(argumentos.workers))
