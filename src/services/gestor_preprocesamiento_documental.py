import os
import subprocess
import tempfile

from pdf2image import convert_from_path

from config import POPPLER_PATH, PREPROCESADOR_DOCUMENTAL, TESSERACT_CMD


class PreprocesamientoNoDisponible(RuntimeError):
    """Indica que el preprocesador solicitado no esta instalado o no respondio."""


def limpiar_imagen_para_ocr(imagen):
    """Mejora contraste y binariza la primera pagina antes de OCR."""
    import cv2
    import numpy as np

    imagen_gris = np.array(imagen.convert("L"))
    imagen_contraste = cv2.convertScaleAbs(imagen_gris, alpha=1.2, beta=0)
    _, imagen_limpia = cv2.threshold(
        imagen_contraste, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU
    )
    return imagen_limpia


def ejecutar_tesseract(imagen_array, idioma="spa", timeout=90):
    """Ejecuta Tesseract con archivo temporal y limpieza garantizada."""
    import cv2

    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as temporal:
        ruta_temporal = temporal.name
    try:
        cv2.imwrite(ruta_temporal, imagen_array)
        comando = [TESSERACT_CMD, ruta_temporal, "stdout", "-l", idioma, "--psm", "6"]
        resultado = subprocess.run(comando, capture_output=True, text=True, timeout=timeout)
        if resultado.returncode != 0:
            raise PreprocesamientoNoDisponible(resultado.stderr)
        return resultado.stdout
    finally:
        if os.path.exists(ruta_temporal):
            os.remove(ruta_temporal)


def extraer_texto_tesseract(ruta_pdf):
    """Extrae texto con el flujo OCR actual basado en pdf2image y Tesseract."""
    paginas = convert_from_path(ruta_pdf, dpi=200, poppler_path=POPPLER_PATH)
    if not paginas:
        return {"texto": "", "metodo": "tesseract", "advertencias": ["PDF sin paginas"]}
    imagen_limpia = limpiar_imagen_para_ocr(paginas[0])
    texto = ejecutar_tesseract(imagen_limpia)
    return {"texto": texto, "metodo": "tesseract", "pagina": paginas[0]}


def extraer_texto_docling(ruta_pdf):
    """Extrae texto estructurado con Docling cuando la dependencia esta instalada."""
    try:
        from docling.document_converter import DocumentConverter
    except ImportError as exc:
        raise PreprocesamientoNoDisponible("Docling no esta instalado") from exc
    resultado = DocumentConverter().convert(ruta_pdf)
    texto = resultado.document.export_to_markdown()
    return {"texto": texto, "metodo": "docling", "pagina": None}


def elegir_metodo_preprocesamiento(tipo_documento, metodo_solicitado=None):
    """Resuelve el metodo por solicitud, tipo documental o configuracion global."""
    preprocesamiento = tipo_documento.get("preprocesamiento", {})
    return (metodo_solicitado or preprocesamiento.get("metodo") or PREPROCESADOR_DOCUMENTAL).lower()


def extraer_texto_documento(ruta_pdf, tipo_documento=None, metodo_solicitado=None):
    """Ejecuta el preprocesador elegido y cae a Tesseract si Docling falla."""
    tipo_documento = tipo_documento or {}
    metodo = elegir_metodo_preprocesamiento(tipo_documento, metodo_solicitado)
    if metodo == "docling":
        return extraer_con_fallback_docling(ruta_pdf)
    return extraer_texto_tesseract(ruta_pdf)


def extraer_con_fallback_docling(ruta_pdf):
    """Intenta Docling y conserva continuidad operativa con Tesseract."""
    try:
        return extraer_texto_docling(ruta_pdf)
    except PreprocesamientoNoDisponible as exc:
        resultado = extraer_texto_tesseract(ruta_pdf)
        resultado["advertencias"] = [str(exc), "Se uso Tesseract como respaldo"]
        return resultado
