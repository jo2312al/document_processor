# ==============================================================================
# SCRIPT: predict.py
#
# PROPOSITO:
# Script de inferencia para la API. Recibe un PDF, aplica OCR y usa el modelo
# spaCy activo del tipo documental indicado para devolver campos estructurados.
# ==============================================================================

import os
import sys
import json
import logging
import argparse
import spacy
import re
from pdf2image import convert_from_path

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))
from config import LOGS_DIR, LOGGING_FORMAT, LOGGING_LEVEL, TESSERACT_CMD
from src.services.gestor_tipos_documento import (
    TipoDocumentoNoEncontrado,
    construir_campos_extraidos,
    obtener_ruta_modelo_activo,
    obtener_tipo_documento,
)
from src.services.gestor_aprendizaje_activo import (
    calcular_confianza_campos,
    registrar_revision_si_aplica,
)
from src.services.gestor_preprocesamiento_documental import (
    ejecutar_tesseract,
    extraer_texto_documento,
    limpiar_imagen_para_ocr,
)

LOG_FILE = os.path.join(LOGS_DIR, 'predict.log')

logging.basicConfig(
    filename=LOG_FILE,
    level=getattr(logging, LOGGING_LEVEL),
    format=LOGGING_FORMAT,
    filemode='a'
)
logger = logging.getLogger(__name__)


def preprocess_image_for_ocr(image):
    """Conserva compatibilidad con codigo anterior de entrenamiento."""
    return limpiar_imagen_para_ocr(image)


def execute_ocr_safely(image_array, lang='spa', timeout=90):
    """Conserva compatibilidad con codigo anterior de entrenamiento."""
    return ejecutar_tesseract(image_array, lang, timeout)


def normalizar_texto_ocr(texto_ocr):
    """Compacta espacios para entregar texto estable al modelo spaCy."""
    return re.sub(r'\s+', ' ', texto_ocr).strip()


def recolectar_entidades(doc):
    """Convierte entidades spaCy en diccionario usando la primera coincidencia."""
    entidades = {}
    for entidad in doc.ents:
        entidades.setdefault(entidad.label_, entidad.text.strip())
    return entidades


def construir_resumen_tipo(tipo_documento):
    """Reduce la configuracion del tipo documental para la respuesta publica."""
    return {
        "id_tipo_documento": tipo_documento["id_tipo_documento"],
        "nombre": tipo_documento["nombre"],
        "modelo_activo": tipo_documento["modelo_activo"],
    }


def obtener_dimensiones_pagina(resultado_preprocesamiento):
    """Devuelve dimensiones si el preprocesador genero imagen de pagina."""
    pagina = resultado_preprocesamiento.get("pagina")
    if not pagina:
        return None
    return {"width": pagina.width, "height": pagina.height}


def predict_entities(pdf_path, id_tipo_documento=None, metodo_preprocesamiento=None):
    """
    Carga el modelo spaCy activo del tipo documental, extrae entidades de un PDF
    y devuelve el resultado en formato compatible con la API.
    """
    logger.info(f"--- Iniciando prediccion para el archivo: {pdf_path} ---")

    try:
        tipo_documento = obtener_tipo_documento(id_tipo_documento)
        ruta_modelo = obtener_ruta_modelo_activo(tipo_documento)
    except TipoDocumentoNoEncontrado as e:
        logger.error(str(e))
        return {"error": str(e)}
    except Exception as e:
        logger.error(f"No se pudo obtener la configuracion documental: {e}")
        return {"error": f"No se pudo obtener la configuracion documental: {e}"}

    if not os.path.exists(ruta_modelo):
        logger.error(f"El directorio del modelo no fue encontrado en: {ruta_modelo}")
        return {"error": "Modelo no encontrado. Ejecuta el pipeline de entrenamiento primero."}

    try:
        nlp = spacy.load(ruta_modelo)
        logger.info(f"Modelo spaCy cargado exitosamente desde: {ruta_modelo}")
    except Exception as e:
        logger.error(f"No se pudo cargar el modelo desde {ruta_modelo}: {e}")
        return {"error": f"No se pudo cargar el modelo: {e}"}

    try:
        resultado_preprocesamiento = extraer_texto_documento(
            pdf_path,
            tipo_documento,
            metodo_preprocesamiento,
        )
        cleaned_text = normalizar_texto_ocr(resultado_preprocesamiento["texto"])
    except Exception as e:
        logger.error(f"Fallo en la fase de procesamiento de PDF/OCR: {e}", exc_info=True)
        return {"error": f"Fallo al procesar el PDF: {e}"}

    doc = nlp(cleaned_text)
    entidades_detectadas = recolectar_entidades(doc)

    campos_extraidos, campos_faltantes = construir_campos_extraidos(
        tipo_documento,
        entidades_detectadas,
    )

    confianza_global = calcular_confianza_campos(campos_extraidos)
    final_json = {
        "tipo_documento": construir_resumen_tipo(tipo_documento),
        "fields": campos_extraidos,
        "campos_faltantes": campos_faltantes,
        "confianza_global": confianza_global,
        "preprocesamiento": {
            "metodo": resultado_preprocesamiento["metodo"],
            "advertencias": resultado_preprocesamiento.get("advertencias", []),
        },
        "image_dimensions": obtener_dimensiones_pagina(resultado_preprocesamiento),
    }
    evento_revision = registrar_revision_si_aplica(
        tipo_documento["id_tipo_documento"],
        os.path.basename(pdf_path),
        final_json,
    )
    final_json["requiere_revision"] = evento_revision is not None

    logger.info(f"Prediccion finalizada. Resultado: {final_json}")
    return final_json


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Extrae entidades de un documento PDF usando un modelo spaCy entrenado."
    )
    parser.add_argument("pdf_path", type=str, help="Ruta al archivo PDF a procesar.")
    parser.add_argument(
        "--tipo-documento",
        type=str,
        default=None,
        help="ID del tipo documental a procesar.",
    )
    args = parser.parse_args()

    if not TESSERACT_CMD or not os.path.exists(TESSERACT_CMD):
        print("Error: La ruta al ejecutable de Tesseract no esta configurada correctamente en 'config.py'.")
    elif not os.path.exists(args.pdf_path):
        print(f"Error: El archivo no fue encontrado en la ruta '{args.pdf_path}'")
    else:
        try:
            prediction_result = predict_entities(args.pdf_path, args.tipo_documento)
            print("\n--- JSON Final ---")
            print(json.dumps(prediction_result, indent=2, ensure_ascii=False))
        except Exception as e:
            logger.critical(f"Error fatal durante la prediccion en modo script: {e}", exc_info=True)
            raise

