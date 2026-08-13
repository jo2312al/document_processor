import json
import os
import re
import uuid
from datetime import datetime, timezone

import pytesseract
from pdf2image import convert_from_path
from pytesseract import Output

from config import POPPLER_PATH, TESSERACT_CMD
from src.services.gestor_tipos_documento import (
    CatalogoDocumentoInvalido,
    cargar_catalogo_tipos_documento,
    guardar_catalogo_tipos_documento,
)


class PlantillaDocumentoInvalida(ValueError):
    """Indica que no se puede construir una plantilla aprendida."""


def crear_plantilla_desde_pdf(id_tipo_documento, ruta_pdf, datos):
    campos_muestra = leer_campos_muestra(datos)
    palabras = extraer_palabras_documento(ruta_pdf)
    plantilla = construir_plantilla(id_tipo_documento, palabras, campos_muestra, datos)
    guardar_plantilla_tipo(id_tipo_documento, plantilla)
    return plantilla


def leer_campos_muestra(datos):
    campos = datos.get("campos_muestra") or {}
    if isinstance(campos, str):
        campos = json.loads(campos)
    if not campos:
        raise PlantillaDocumentoInvalida("campos_muestra es obligatorio.")
    return campos


def extraer_palabras_documento(ruta_pdf):
    paginas = convert_from_path(ruta_pdf, dpi=200, poppler_path=POPPLER_PATH)
    if not paginas:
        raise PlantillaDocumentoInvalida("El PDF no tiene paginas.")
    return extraer_palabras_pagina(paginas[0])


def extraer_palabras_pagina(pagina):
    pytesseract.pytesseract.tesseract_cmd = TESSERACT_CMD
    datos = pytesseract.image_to_data(pagina, lang="spa", output_type=Output.DICT)
    return [crear_palabra(datos, indice) for indice in range(len(datos["text"])) if palabra_valida(datos, indice)]


def palabra_valida(datos, indice):
    return (datos["text"][indice] or "").strip() and int(float(datos["conf"][indice])) >= 0


def crear_palabra(datos, indice):
    return {
        "texto": datos["text"][indice].strip(),
        "pagina": 1,
        "x": int(datos["left"][indice]),
        "y": int(datos["top"][indice]),
        "ancho": int(datos["width"][indice]),
        "alto": int(datos["height"][indice]),
        "confianza": int(float(datos["conf"][indice])),
    }


def construir_plantilla(id_tipo_documento, palabras, campos_muestra, datos):
    campos = [ubicar_campo(clave, valor, palabras) for clave, valor in campos_muestra.items()]
    return {
        "id_plantilla": str(uuid.uuid4()),
        "id_tipo_documento": id_tipo_documento,
        "nombre": datos.get("nombre_plantilla") or "Plantilla aprendida",
        "estado": "borrador",
        "origen": "ocr_con_coordenadas",
        "texto_base": " ".join(palabra["texto"] for palabra in palabras),
        "campos": campos,
        "fecha_creacion": datetime.now(timezone.utc).isoformat(),
    }


def ubicar_campo(clave, valor, palabras):
    coincidencia = buscar_secuencia(str(valor), palabras)
    return {
        "clave_campo": clave,
        "texto_detectado": str(valor),
        "ubicacion": calcular_ubicacion(coincidencia),
        "frases_cercanas": obtener_contexto(coincidencia, palabras),
        "confianza": calcular_confianza(coincidencia),
    }


def buscar_secuencia(valor, palabras):
    tokens = normalizar_texto(valor).split()
    normalizadas = [normalizar_texto(palabra["texto"]) for palabra in palabras]
    for indice in range(0, len(normalizadas) - len(tokens) + 1):
        if normalizadas[indice : indice + len(tokens)] == tokens:
            return palabras[indice : indice + len(tokens)]
    return []


def normalizar_texto(texto):
    texto = texto.lower().strip()
    return re.sub(r"[^a-z0-9áéíóúñü]+", " ", texto).strip()


def calcular_ubicacion(palabras):
    if not palabras:
        return {"pagina": 1, "x": 0, "y": 0, "ancho": 0, "alto": 0}
    x = min(palabra["x"] for palabra in palabras)
    y = min(palabra["y"] for palabra in palabras)
    derecha = max(palabra["x"] + palabra["ancho"] for palabra in palabras)
    abajo = max(palabra["y"] + palabra["alto"] for palabra in palabras)
    return {"pagina": 1, "x": x, "y": y, "ancho": derecha - x, "alto": abajo - y}


def obtener_contexto(coincidencia, palabras):
    if not coincidencia:
        return []
    inicio = palabras.index(coincidencia[0])
    fin = palabras.index(coincidencia[-1])
    ventana = palabras[max(0, inicio - 5) : min(len(palabras), fin + 6)]
    return [" ".join(palabra["texto"] for palabra in ventana)]


def calcular_confianza(palabras):
    if not palabras:
        return 0
    return round(sum(palabra["confianza"] for palabra in palabras) / len(palabras), 2)


def guardar_plantilla_tipo(id_tipo_documento, plantilla):
    catalogo = cargar_catalogo_tipos_documento()
    tipo = buscar_tipo(catalogo, id_tipo_documento)
    tipo.setdefault("plantillas", []).append(plantilla)
    tipo["plantilla_activa"] = plantilla["id_plantilla"]
    guardar_catalogo_tipos_documento(catalogo)


def buscar_tipo(catalogo, id_tipo_documento):
    for tipo in catalogo.get("tipos_documento", []):
        if tipo.get("id_tipo_documento") == id_tipo_documento:
            return tipo
    raise CatalogoDocumentoInvalido(f"No existe el tipo de documento: {id_tipo_documento}")
