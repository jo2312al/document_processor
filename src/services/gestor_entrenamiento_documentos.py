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
    return [doc for doc in indice.get("documentos_entrenamiento", []) if doc.get("id_tipo_documento") == id_tipo_documento]


def obtener_documento_entrenamiento(id_documento_entrenamiento):
    for documento in cargar_indice_documentos().get("documentos_entrenamiento", []):
        if documento.get("id_documento_entrenamiento") == id_documento_entrenamiento:
            return documento
    raise DocumentoEntrenamientoNoEncontrado(_mensaje_no_encontrado(id_documento_entrenamiento))


def crear_documento_entrenamiento(id_tipo_documento, archivo_origen, nombre_archivo, texto_ocr):
    _validar_documento(id_tipo_documento, nombre_archivo)
    id_documento = str(uuid.uuid4())
    ruta_destino = _copiar_documento(id_tipo_documento, id_documento, archivo_origen)
    documento = _crear_registro_documento(id_documento, id_tipo_documento, nombre_archivo, ruta_destino, texto_ocr)
    _agregar_documento_indice(documento)
    return documento


def agregar_anotacion_entrenamiento(id_documento_entrenamiento, datos_anotacion):
    anotacion = _normalizar_anotacion(datos_anotacion)
    indice = cargar_indice_documentos()
    documento = _buscar_documento_en_indice(indice, id_documento_entrenamiento)
    documento.setdefault("anotaciones", []).append(anotacion)
    documento["estado"] = "anotado"
    guardar_indice_documentos(indice)
    return anotacion


def _validar_documento(id_tipo_documento, nombre_archivo):
    if not id_tipo_documento:
        raise DocumentoEntrenamientoInvalido("El tipo de documento es obligatorio.")
    if not nombre_archivo.lower().endswith(".pdf"):
        raise DocumentoEntrenamientoInvalido("Solo se aceptan documentos PDF.")


def _copiar_documento(id_tipo_documento, id_documento, archivo_origen):
    carpeta_tipo = os.path.join(DOCUMENTOS_ENTRENAMIENTO_DIR, id_tipo_documento)
    os.makedirs(carpeta_tipo, exist_ok=True)
    ruta_destino = os.path.join(carpeta_tipo, f"{id_documento}.pdf")
    shutil.copyfile(archivo_origen, ruta_destino)
    return ruta_destino


def _crear_registro_documento(id_documento, id_tipo_documento, nombre_archivo, ruta_destino, texto_ocr):
    return {
        "id_documento_entrenamiento": id_documento,
        "id_tipo_documento": id_tipo_documento,
        "nombre_archivo": nombre_archivo,
        "ruta_archivo": ruta_destino,
        "texto_ocr": texto_ocr,
        "estado": "ocr_generado" if texto_ocr else "cargado",
        "anotaciones": [],
        "fecha_carga": _fecha_actual(),
    }


def _agregar_documento_indice(documento):
    indice = cargar_indice_documentos()
    indice.setdefault("documentos_entrenamiento", []).append(documento)
    guardar_indice_documentos(indice)


def _normalizar_anotacion(datos_anotacion):
    texto = (datos_anotacion.get("texto_anotado") or "").strip()
    etiqueta = (datos_anotacion.get("etiqueta_entidad") or "").strip().upper()
    clave = (datos_anotacion.get("clave_campo") or "").strip()
    _validar_datos_anotacion(texto, etiqueta, clave)
    inicio, fin = _obtener_rango_anotacion(datos_anotacion)
    return _crear_registro_anotacion(clave, etiqueta, texto, inicio, fin, datos_anotacion)


def _validar_datos_anotacion(texto, etiqueta, clave):
    if not texto or not etiqueta or not clave:
        raise DocumentoEntrenamientoInvalido("La anotacion requiere clave_campo, etiqueta_entidad y texto_anotado.")


def _obtener_rango_anotacion(datos_anotacion):
    try:
        inicio = int(datos_anotacion.get("posicion_inicio"))
        fin = int(datos_anotacion.get("posicion_fin"))
    except (TypeError, ValueError):
        raise DocumentoEntrenamientoInvalido("Las posiciones de la anotacion son obligatorias.")
    _validar_rango_anotacion(inicio, fin)
    return inicio, fin


def _validar_rango_anotacion(inicio, fin):
    if inicio < 0 or fin <= inicio:
        raise DocumentoEntrenamientoInvalido("El rango de la anotacion no es valido.")


def _crear_registro_anotacion(clave, etiqueta, texto, inicio, fin, datos):
    return {
        "id_anotacion_entrenamiento": str(uuid.uuid4()),
        "clave_campo": clave,
        "etiqueta_entidad": etiqueta,
        "texto_anotado": texto,
        "posicion_inicio": inicio,
        "posicion_fin": fin,
        "validado": bool(datos.get("validado", True)),
        "fecha_anotacion": _fecha_actual(),
    }


def _buscar_documento_en_indice(indice, id_documento_entrenamiento):
    for documento in indice.get("documentos_entrenamiento", []):
        if documento.get("id_documento_entrenamiento") == id_documento_entrenamiento:
            return documento
    raise DocumentoEntrenamientoNoEncontrado(_mensaje_no_encontrado(id_documento_entrenamiento))


def _mensaje_no_encontrado(id_documento_entrenamiento):
    return f"No existe el documento de entrenamiento: {id_documento_entrenamiento}"


def _fecha_actual():
    return datetime.now(timezone.utc).isoformat()
