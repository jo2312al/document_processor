import hashlib
import json
import os
from datetime import datetime, timezone

from pdf2image import convert_from_path

from config import POPPLER_PATH
from src.services.gestor_lotes_aprendizaje import registrar_documento_validado
from src.services.preparador_entrenamiento_servicio_social import (
    TIPO_CARTA_TERMINACION,
    campos_obligatorios_faltantes,
    guardar_pagina_pdf,
)

DIRECTORIO_REVISION = os.path.join("output", "entrenamiento_servicio_social_lote_20260904")
REPORTE_REVISION = os.path.join(DIRECTORIO_REVISION, "reporte_preparacion.json")


class RegistroRevisionNoEncontrado(ValueError):
    pass


class RegistroRevisionInvalido(ValueError):
    pass


def listar_registros_revision():
    registros = cargar_reporte_revision().get("registros", [])
    return [resumir_registro(registro) for registro in registros]


def obtener_registro_revision(id_revision):
    registro = buscar_registro_revision(id_revision)
    return {**resumir_registro(registro), "texto_ocr": registro.get("texto_ocr", "")}


def guardar_correccion_revision(id_revision, campos_corregidos):
    reporte = cargar_reporte_revision()
    registro = buscar_registro_en_reporte(reporte, id_revision)
    validar_correccion(campos_corregidos)
    if registro.get("documento_validado"):
        return crear_respuesta_existente(registro)
    resultado = registrar_registro_corregido(registro, campos_corregidos)
    guardar_reporte_revision(reporte)
    return resultado


def cargar_reporte_revision():
    if not os.path.exists(REPORTE_REVISION):
        return {"resumen": {}, "registros": []}
    with open(REPORTE_REVISION, "r", encoding="utf-8") as archivo:
        return json.load(archivo)


def guardar_reporte_revision(reporte):
    with open(REPORTE_REVISION, "w", encoding="utf-8") as archivo:
        json.dump(reporte, archivo, ensure_ascii=False, indent=2)
        archivo.write("\n")


def resumir_registro(registro):
    campos = registro.get("campos_validados", {})
    faltantes = campos_obligatorios_faltantes(campos)
    return {
        "id_revision": construir_id_revision(registro),
        "archivo_origen": registro.get("archivo_origen", ""),
        "pagina": registro.get("pagina"),
        "clasificacion": registro.get("clasificacion", {}),
        "campos_validados": campos,
        "campos_faltantes": faltantes,
        "apto_entrenamiento": tiene_campos_utiles(campos),
        "documento_validado": registro.get("documento_validado"),
    }


def construir_id_revision(registro):
    llave = f"{registro.get('archivo_origen')}|{registro.get('pagina')}"
    return hashlib.sha1(llave.encode("utf-8")).hexdigest()[:16]


def buscar_registro_revision(id_revision):
    return buscar_registro_en_reporte(cargar_reporte_revision(), id_revision)


def buscar_registro_en_reporte(reporte, id_revision):
    for registro in reporte.get("registros", []):
        if construir_id_revision(registro) == id_revision:
            return registro
    raise RegistroRevisionNoEncontrado(f"No existe el registro de revision: {id_revision}")


def validar_correccion(campos):
    if not tiene_campos_utiles(campos):
        raise RegistroRevisionInvalido("Agrega al menos un dato encontrado para entrenar.")


def tiene_campos_utiles(campos):
    return any(str(valor or "").strip() for valor in campos.values())


def crear_respuesta_existente(registro):
    return {
        "estado": "ya_validado",
        "registro": resumir_registro(registro),
        "documento_validado": registro.get("documento_validado"),
    }


def registrar_registro_corregido(registro, campos_corregidos):
    pagina = cargar_pagina_pdf(registro)
    registro["campos_validados"] = campos_corregidos
    registro["campos_faltantes"] = campos_obligatorios_faltantes(campos_corregidos)
    registro["apto_entrenamiento"] = True
    registro["documento_validado"] = registrar_pagina_corregida(registro, pagina)
    registro["fecha_revision"] = datetime.now(timezone.utc).isoformat()
    return {"estado": "validado", "registro": resumir_registro(registro)}


def cargar_pagina_pdf(registro):
    paginas = convert_from_path(
        registro["archivo_origen"],
        dpi=200,
        poppler_path=POPPLER_PATH,
        first_page=int(registro["pagina"]),
        last_page=int(registro["pagina"]),
    )
    return paginas[0]


def registrar_pagina_corregida(registro, pagina):
    ruta_pagina = guardar_pagina_pdf(registro, pagina, DIRECTORIO_REVISION)
    documento, lote = registrar_documento_validado(
        TIPO_CARTA_TERMINACION,
        ruta_pagina,
        os.path.basename(ruta_pagina),
        registro["campos_validados"],
        registro.get("texto_ocr", ""),
    )
    return {"id_documento_validado": documento["id_documento_validado"], "id_lote": lote["id_lote"]}
