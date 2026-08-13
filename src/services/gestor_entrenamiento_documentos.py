import json
import os
import shutil
import uuid
from datetime import datetime, timezone

from config import DOCUMENTOS_ENTRENAMIENTO_DIR

INDICE_DOCUMENTOS_PATH = os.path.join(DOCUMENTOS_ENTRENAMIENTO_DIR, "indice_documentos.json")


class DocumentoEntrenamientoNoEncontrado(ValueError):
    """Indica que el documento de entrenamiento solicitado no existe."""


class DocumentoEntrenamientoInvalido(ValueError):
    """Indica que el documento o anotacion no cumple los datos minimos."""


def cargar_indice_documentos():
    if not os.path.exists(INDICE_DOCUMENTOS_PATH):
        return {"documentos_entrenamiento": []}

    with open(INDICE_DOCUMENTOS_PATH, "r", encoding="utf-8") as archivo:
        return json.load(archivo)


def guardar_indice_documentos(indice):
    os.makedirs(DOCUMENTOS_ENTRENAMIENTO_DIR, exist_ok=True)
    with open(INDICE_DOCUMENTOS_PATH, "w", encoding="utf-8") as archivo:
        json.dump(indice, archivo, ensure_ascii=False, indent=2)
        archivo.write("\n")


def listar_documentos_entrenamiento(id_tipo_documento):
    indice = cargar_indice_documentos()
    return [
        documento
        for documento in indice.get("documentos_entrenamiento", [])
        if documento.get("id_tipo_documento") == id_tipo_documento
    ]


def obtener_documento_entrenamiento(id_documento_entrenamiento):
    indice = cargar_indice_documentos()
    for documento in indice.get("documentos_entrenamiento", []):
        if documento.get("id_documento_entrenamiento") == id_documento_entrenamiento:
            return documento

    raise DocumentoEntrenamientoNoEncontrado(
        f"No existe el documento de entrenamiento: {id_documento_entrenamiento}"
    )


def crear_documento_entrenamiento(id_tipo_documento, archivo_origen, nombre_archivo, texto_ocr):
    if not id_tipo_documento:
        raise DocumentoEntrenamientoInvalido("El tipo de documento es obligatorio.")
    if not nombre_archivo.lower().endswith(".pdf"):
        raise DocumentoEntrenamientoInvalido("Solo se aceptan documentos PDF.")

    id_documento = str(uuid.uuid4())
    carpeta_tipo = os.path.join(DOCUMENTOS_ENTRENAMIENTO_DIR, id_tipo_documento)
    os.makedirs(carpeta_tipo, exist_ok=True)

    nombre_seguro = f"{id_documento}.pdf"
    ruta_destino = os.path.join(carpeta_tipo, nombre_seguro)
    shutil.copyfile(archivo_origen, ruta_destino)

    documento = {
        "id_documento_entrenamiento": id_documento,
        "id_tipo_documento": id_tipo_documento,
        "nombre_archivo": nombre_archivo,
        "ruta_archivo": ruta_destino,
        "texto_ocr": texto_ocr,
        "estado": "ocr_generado" if texto_ocr else "cargado",
        "anotaciones": [],
        "fecha_carga": datetime.now(timezone.utc).isoformat(),
    }

    indice = cargar_indice_documentos()
    indice.setdefault("documentos_entrenamiento", []).append(documento)
    guardar_indice_documentos(indice)
    return documento


def agregar_anotacion_entrenamiento(id_documento_entrenamiento, datos_anotacion):
    texto_anotado = (datos_anotacion.get("texto_anotado") or "").strip()
    etiqueta_entidad = (datos_anotacion.get("etiqueta_entidad") or "").strip().upper()
    clave_campo = (datos_anotacion.get("clave_campo") or "").strip()

    if not texto_anotado or not etiqueta_entidad or not clave_campo:
        raise DocumentoEntrenamientoInvalido(
            "La anotacion requiere clave_campo, etiqueta_entidad y texto_anotado."
        )

    try:
        posicion_inicio = int(datos_anotacion.get("posicion_inicio"))
        posicion_fin = int(datos_anotacion.get("posicion_fin"))
    except (TypeError, ValueError):
        raise DocumentoEntrenamientoInvalido("Las posiciones de la anotacion son obligatorias.")

    if posicion_inicio < 0 or posicion_fin <= posicion_inicio:
        raise DocumentoEntrenamientoInvalido("El rango de la anotacion no es valido.")

    indice = cargar_indice_documentos()
    for documento in indice.get("documentos_entrenamiento", []):
        if documento.get("id_documento_entrenamiento") == id_documento_entrenamiento:
            anotacion = {
                "id_anotacion_entrenamiento": str(uuid.uuid4()),
                "clave_campo": clave_campo,
                "etiqueta_entidad": etiqueta_entidad,
                "texto_anotado": texto_anotado,
                "posicion_inicio": posicion_inicio,
                "posicion_fin": posicion_fin,
                "validado": bool(datos_anotacion.get("validado", True)),
                "fecha_anotacion": datetime.now(timezone.utc).isoformat(),
            }
            documento.setdefault("anotaciones", []).append(anotacion)
            documento["estado"] = "anotado"
            guardar_indice_documentos(indice)
            return anotacion

    raise DocumentoEntrenamientoNoEncontrado(
        f"No existe el documento de entrenamiento: {id_documento_entrenamiento}"
    )
