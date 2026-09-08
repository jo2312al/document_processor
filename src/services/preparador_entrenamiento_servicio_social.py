import json
import os
from datetime import datetime, timezone

from pdf2image import convert_from_path

from config import POPPLER_PATH
from src.services.extractor_servicio_social import (
    clasificar_servicio_social,
    extraer_entidades_servicio_social,
)
from src.services.gestor_lotes_aprendizaje import registrar_documento_validado
from src.services.gestor_preprocesamiento_documental import (
    ejecutar_tesseract,
    limpiar_imagen_para_ocr,
)

TIPO_CARTA_TERMINACION = "carta_terminacion_servicio_social"
DIRECTORIO_SALIDA = os.path.join("output", "entrenamiento_servicio_social")


def preparar_fuentes_entrenamiento(rutas_pdf, directorio_salida=DIRECTORIO_SALIDA, registrar=True):
    directorio_salida = directorio_salida or DIRECTORIO_SALIDA
    os.makedirs(directorio_salida, exist_ok=True)
    registros = []
    for ruta_pdf in rutas_pdf:
        registros.extend(procesar_pdf_fuente(ruta_pdf, directorio_salida, registrar))
    resumen = construir_resumen(registros)
    guardar_reporte(directorio_salida, registros, resumen)
    return {"resumen": resumen, "registros": registros}


def procesar_pdf_fuente(ruta_pdf, directorio_salida, registrar=True):
    paginas = convert_from_path(ruta_pdf, dpi=200, poppler_path=POPPLER_PATH)
    return [
        procesar_pagina(ruta_pdf, pagina, indice + 1, directorio_salida, registrar)
        for indice, pagina in enumerate(paginas)
    ]


def procesar_pagina(ruta_pdf, pagina, numero_pagina, directorio_salida, registrar=True):
    texto = extraer_texto_pagina(pagina)
    campos = mapear_campos(extraer_entidades_servicio_social(texto))
    registro = crear_registro(ruta_pdf, numero_pagina, texto, campos)
    if registro["apto_entrenamiento"] and registrar:
        registro["documento_validado"] = registrar_pagina(registro, pagina, directorio_salida)
    return registro


def extraer_texto_pagina(pagina):
    imagen_limpia = limpiar_imagen_para_ocr(pagina)
    return ejecutar_tesseract(imagen_limpia)


def mapear_campos(entidades):
    return {
        "numero_control": entidades.get("MATRICULA", ""),
        "nombre_estudiante": entidades.get("NOMBRE_COMPLETO", ""),
        "carrera": entidades.get("CARRERA", ""),
        "dependencia": entidades.get("DEPENDENCIA", ""),
        "programa": entidades.get("PROGRAMA", ""),
        "periodo": entidades.get("SERVICIO", ""),
        "horas": entidades.get("HORAS", ""),
        "oficio": entidades.get("OFICIO", ""),
        "responsable": entidades.get("RESPONSABLE", ""),
    }


def crear_registro(ruta_pdf, numero_pagina, texto, campos):
    faltantes = campos_obligatorios_faltantes(campos)
    return {
        "archivo_origen": ruta_pdf,
        "pagina": numero_pagina,
        "clasificacion": clasificar_servicio_social(texto),
        "campos_validados": campos,
        "campos_faltantes": faltantes,
        "apto_entrenamiento": tiene_campos_utiles(campos),
        "texto_ocr": texto,
    }


def campos_obligatorios_faltantes(campos):
    obligatorios = ["numero_control", "nombre_estudiante", "carrera", "periodo"]
    return [campo for campo in obligatorios if not str(campos.get(campo, "")).strip()]


def tiene_campos_utiles(campos):
    return any(str(valor or "").strip() for valor in campos.values())


def registrar_pagina(registro, pagina, directorio_salida):
    ruta_pagina = guardar_pagina_pdf(registro, pagina, directorio_salida)
    nombre = os.path.basename(ruta_pagina)
    documento, lote = registrar_documento_validado(
        TIPO_CARTA_TERMINACION,
        ruta_pagina,
        nombre,
        registro["campos_validados"],
        registro["texto_ocr"],
    )
    return {"id_documento_validado": documento["id_documento_validado"], "id_lote": lote["id_lote"]}


def guardar_pagina_pdf(registro, pagina, directorio_salida):
    nombre_base = crear_nombre_pagina(registro)
    ruta_pagina = os.path.join(directorio_salida, f"{nombre_base}.pdf")
    pagina.convert("RGB").save(ruta_pagina, "PDF", resolution=200)
    return ruta_pagina


def crear_nombre_pagina(registro):
    origen = os.path.splitext(os.path.basename(registro["archivo_origen"]))[0]
    origen = "".join(caracter if caracter.isalnum() else "_" for caracter in origen)
    return f"{origen}_pagina_{registro['pagina']:03d}"


def construir_resumen(registros):
    aptos = [registro for registro in registros if registro["apto_entrenamiento"]]
    return {
        "fecha": datetime.now(timezone.utc).isoformat(),
        "paginas_procesadas": len(registros),
        "aptas_entrenamiento": len(aptos),
        "rechazadas_revision": len(registros) - len(aptos),
    }


def guardar_reporte(directorio_salida, registros, resumen):
    ruta = os.path.join(directorio_salida, "reporte_preparacion.json")
    with open(ruta, "w", encoding="utf-8") as archivo:
        json.dump({"resumen": resumen, "registros": registros}, archivo, ensure_ascii=False, indent=2)
        archivo.write("\n")
