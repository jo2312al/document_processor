import argparse
import json
import logging
import os
import re
import sys

import spacy

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from config import LOGGING_FORMAT, LOGGING_LEVEL, LOGS_DIR, TESSERACT_CMD
from src.services.gestor_aprendizaje_activo import (
    calcular_confianza_campos,
    registrar_revision_si_aplica,
)
from src.services.gestor_preprocesamiento_documental import (
    ejecutar_tesseract,
    extraer_texto_documento,
    limpiar_imagen_para_ocr,
)
from src.services.gestor_tipos_documento import (
    TipoDocumentoNoEncontrado,
    construir_campos_extraidos,
    obtener_ruta_modelo_activo,
    obtener_tipo_documento,
)

ARCHIVO_LOG = os.path.join(LOGS_DIR, "predict.log")
logging.basicConfig(
    filename=ARCHIVO_LOG,
    level=getattr(logging, LOGGING_LEVEL),
    format=LOGGING_FORMAT,
    filemode="a",
)
registrador = logging.getLogger(__name__)


def preprocesar_imagen_para_ocr(imagen):
    return limpiar_imagen_para_ocr(imagen)


def ejecutar_ocr_seguro(imagen, idioma="spa", tiempo_limite=90):
    return ejecutar_tesseract(imagen, idioma, tiempo_limite)


def preprocess_image_for_ocr(image):
    return preprocesar_imagen_para_ocr(image)


def execute_ocr_safely(image_array, lang="spa", timeout=90):
    return ejecutar_ocr_seguro(image_array, lang, timeout)


def normalizar_texto_ocr(texto_ocr):
    return re.sub(r"\s+", " ", texto_ocr).strip()


def recolectar_entidades(documento_spacy):
    entidades = {}
    for entidad in documento_spacy.ents:
        entidades.setdefault(entidad.label_, entidad.text.strip())
    return entidades


def construir_resumen_tipo(tipo_documento):
    return {
        "id_tipo_documento": tipo_documento["id_tipo_documento"],
        "nombre": tipo_documento["nombre"],
        "modelo_activo": tipo_documento["modelo_activo"],
    }


def obtener_dimensiones_pagina(resultado_preprocesamiento):
    pagina = resultado_preprocesamiento.get("pagina")
    if not pagina:
        return None
    return {"width": pagina.width, "height": pagina.height}


def predecir_entidades(ruta_pdf, id_tipo_documento=None, metodo_preprocesamiento=None):
    registrador.info("Iniciando prediccion para: %s", ruta_pdf)
    contexto = _preparar_contexto_prediccion(id_tipo_documento)
    if "error" in contexto:
        return contexto

    resultado_ocr = _extraer_texto_ocr(ruta_pdf, contexto["tipo_documento"], metodo_preprocesamiento)
    if "error" in resultado_ocr:
        return resultado_ocr

    entidades = _detectar_entidades(contexto["modelo"], resultado_ocr["texto"])
    respuesta = _construir_respuesta(contexto["tipo_documento"], entidades, resultado_ocr)
    _marcar_revision_si_corresponde(ruta_pdf, respuesta)
    return respuesta


def predict_entities(pdf_path, id_tipo_documento=None, metodo_preprocesamiento=None):
    return predecir_entidades(pdf_path, id_tipo_documento, metodo_preprocesamiento)


def _preparar_contexto_prediccion(id_tipo_documento):
    tipo_documento = _obtener_tipo_seguro(id_tipo_documento)
    if "error" in tipo_documento:
        return tipo_documento
    modelo = _cargar_modelo_seguro(tipo_documento)
    if "error" in modelo:
        return modelo
    return {"tipo_documento": tipo_documento, "modelo": modelo}


def _obtener_tipo_seguro(id_tipo_documento):
    try:
        return obtener_tipo_documento(id_tipo_documento)
    except TipoDocumentoNoEncontrado as error:
        registrador.error(str(error))
        return {"error": str(error)}
    except Exception as error:
        mensaje = f"No se pudo obtener la configuracion documental: {error}"
        registrador.error(mensaje)
        return {"error": mensaje}


def _cargar_modelo_seguro(tipo_documento):
    ruta_modelo = obtener_ruta_modelo_activo(tipo_documento)
    if not os.path.exists(ruta_modelo):
        return {"error": "Modelo no encontrado. Ejecuta el pipeline de entrenamiento primero."}
    try:
        return spacy.load(ruta_modelo)
    except Exception as error:
        registrador.error("No se pudo cargar el modelo: %s", error)
        return {"error": f"No se pudo cargar el modelo: {error}"}


def _extraer_texto_ocr(ruta_pdf, tipo_documento, metodo_preprocesamiento):
    try:
        resultado = extraer_texto_documento(ruta_pdf, tipo_documento, metodo_preprocesamiento)
        resultado["texto"] = normalizar_texto_ocr(resultado["texto"])
        return resultado
    except Exception as error:
        registrador.error("Fallo procesando PDF/OCR: %s", error, exc_info=True)
        return {"error": f"Fallo al procesar el PDF: {error}"}


def _detectar_entidades(modelo, texto_ocr):
    documento_spacy = modelo(texto_ocr)
    return recolectar_entidades(documento_spacy)


def _construir_respuesta(tipo_documento, entidades, resultado_ocr):
    campos, faltantes = construir_campos_extraidos(tipo_documento, entidades)
    return {
        "tipo_documento": construir_resumen_tipo(tipo_documento),
        "fields": campos,
        "campos_faltantes": faltantes,
        "confianza_global": calcular_confianza_campos(campos),
        "preprocesamiento": _resumir_preprocesamiento(resultado_ocr),
        "image_dimensions": obtener_dimensiones_pagina(resultado_ocr),
    }


def _resumir_preprocesamiento(resultado_ocr):
    return {
        "metodo": resultado_ocr["metodo"],
        "advertencias": resultado_ocr.get("advertencias", []),
    }


def _marcar_revision_si_corresponde(ruta_pdf, respuesta):
    tipo_documento = respuesta["tipo_documento"]["id_tipo_documento"]
    evento = registrar_revision_si_aplica(tipo_documento, os.path.basename(ruta_pdf), respuesta)
    respuesta["requiere_revision"] = evento is not None


def _crear_argumentos_cli():
    parser = argparse.ArgumentParser(description="Extrae entidades de un PDF con spaCy.")
    parser.add_argument("pdf_path", type=str, help="Ruta del PDF a procesar.")
    parser.add_argument("--tipo-documento", type=str, default=None)
    return parser.parse_args()


def _validar_cli(ruta_pdf):
    if not TESSERACT_CMD or not os.path.exists(TESSERACT_CMD):
        return "La ruta de Tesseract no esta configurada correctamente."
    if not os.path.exists(ruta_pdf):
        return f"El archivo no fue encontrado: {ruta_pdf}"
    return None


def _ejecutar_cli():
    argumentos = _crear_argumentos_cli()
    error = _validar_cli(argumentos.pdf_path)
    if error:
        print(f"Error: {error}")
        return
    resultado = predecir_entidades(argumentos.pdf_path, argumentos.tipo_documento)
    print(json.dumps(resultado, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    _ejecutar_cli()
