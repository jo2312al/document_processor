import json
import os
import shutil
import uuid
from datetime import datetime, timezone

from config import APRENDIZAJE_LOTES_PATH, DOCUMENTOS_VALIDADOS_DIR, UMBRAL_LOTE_ENTRENAMIENTO

CAMPOS_OBLIGATORIOS = ["alu_matricula", "NOMBRE_COMPLETO", "alu_carrera", "alu_servicio"]


class DocumentoValidadoInvalido(ValueError):
    pass


class LoteAprendizajeNoEncontrado(ValueError):
    pass


def cargar_estado_aprendizaje():
    if not os.path.exists(APRENDIZAJE_LOTES_PATH):
        return {"lotes": [], "documentos_validados": [], "configuracion": _configuracion_inicial()}
    with open(APRENDIZAJE_LOTES_PATH, "r", encoding="utf-8") as archivo:
        return json.load(archivo)


def guardar_estado_aprendizaje(estado):
    os.makedirs(os.path.dirname(APRENDIZAJE_LOTES_PATH), exist_ok=True)
    with open(APRENDIZAJE_LOTES_PATH, "w", encoding="utf-8") as archivo:
        json.dump(estado, archivo, ensure_ascii=False, indent=2)
        archivo.write("\n")


def listar_lotes_aprendizaje(id_tipo_documento=None):
    estado = cargar_estado_aprendizaje()
    lotes = estado.get("lotes", [])
    if id_tipo_documento:
        lotes = [lote for lote in lotes if lote.get("id_tipo_documento") == id_tipo_documento]
    return {"configuracion": estado.get("configuracion", {}), "lotes": lotes}


def registrar_documento_validado(id_tipo_documento, ruta_pdf, nombre_archivo, campos, texto_ocr):
    _validar_documento_validado(id_tipo_documento, nombre_archivo, campos)
    estado = cargar_estado_aprendizaje()
    lote = obtener_o_crear_lote_abierto(estado, id_tipo_documento)
    documento = _crear_documento_validado(id_tipo_documento, ruta_pdf, nombre_archivo, campos, texto_ocr)
    estado.setdefault("documentos_validados", []).append(documento)
    lote.setdefault("documentos", []).append(documento["id_documento_validado"])
    _actualizar_estado_lote(lote, estado)
    guardar_estado_aprendizaje(estado)
    return documento, lote


def marcar_lote_en_cola(id_lote, id_tarea=None):
    lote, estado = obtener_lote_con_estado(id_lote)
    lote["estado"] = "en_cola"
    lote["id_tarea"] = id_tarea
    lote["fecha_encolado"] = _fecha_actual()
    guardar_estado_aprendizaje(estado)
    return lote


def actualizar_lote(id_lote, **campos):
    lote, estado = obtener_lote_con_estado(id_lote)
    lote.update(campos)
    lote["fecha_actualizacion"] = _fecha_actual()
    guardar_estado_aprendizaje(estado)
    return lote


def obtener_lote_con_estado(id_lote):
    estado = cargar_estado_aprendizaje()
    for lote in estado.get("lotes", []):
        if lote.get("id_lote") == id_lote:
            return lote, estado
    raise LoteAprendizajeNoEncontrado(f"No existe el lote: {id_lote}")


def obtener_documentos_lote(id_lote):
    lote, estado = obtener_lote_con_estado(id_lote)
    ids_documentos = set(lote.get("documentos", []))
    documentos = estado.get("documentos_validados", [])
    return [doc for doc in documentos if doc.get("id_documento_validado") in ids_documentos]


def obtener_umbral_lote():
    estado = cargar_estado_aprendizaje()
    return int(estado.get("configuracion", {}).get("umbral_lote", UMBRAL_LOTE_ENTRENAMIENTO))


def lote_listo_para_entrenar(lote):
    return len(lote.get("documentos", [])) >= obtener_umbral_lote()


def _configuracion_inicial():
    return {"umbral_lote": UMBRAL_LOTE_ENTRENAMIENTO, "validacion_lote": 0.2}


def obtener_o_crear_lote_abierto(estado, id_tipo_documento):
    for lote in estado.get("lotes", []):
        if lote.get("id_tipo_documento") == id_tipo_documento and lote.get("estado") == "recibiendo_documentos":
            return lote
    return _agregar_lote_abierto(estado, id_tipo_documento)


def _agregar_lote_abierto(estado, id_tipo_documento):
    lote = _crear_lote(id_tipo_documento)
    estado.setdefault("lotes", []).append(lote)
    return lote


def _crear_lote(id_tipo_documento):
    return {
        "id_lote": str(uuid.uuid4()),
        "id_tipo_documento": id_tipo_documento,
        "estado": "recibiendo_documentos",
        "documentos": [],
        "metricas": {},
        "recomendaciones": [],
        "fecha_creacion": _fecha_actual(),
    }


def _validar_documento_validado(id_tipo_documento, nombre_archivo, campos):
    if not id_tipo_documento:
        raise DocumentoValidadoInvalido("El tipo de documento es obligatorio.")
    if not nombre_archivo.lower().endswith(".pdf"):
        raise DocumentoValidadoInvalido("Solo se aceptan documentos PDF.")
    _validar_campos_obligatorios(campos)


def _validar_campos_obligatorios(campos):
    faltantes = [campo for campo in CAMPOS_OBLIGATORIOS if not str(campos.get(campo, "")).strip()]
    if faltantes:
        raise DocumentoValidadoInvalido(f"Faltan campos validados: {', '.join(faltantes)}")


def _crear_documento_validado(id_tipo_documento, ruta_pdf, nombre_archivo, campos, texto_ocr):
    id_documento = str(uuid.uuid4())
    ruta_destino = _copiar_pdf_validado(id_tipo_documento, id_documento, ruta_pdf)
    return _registro_documento(id_documento, id_tipo_documento, nombre_archivo, ruta_destino, campos, texto_ocr)


def _copiar_pdf_validado(id_tipo_documento, id_documento, ruta_pdf):
    carpeta_tipo = os.path.join(DOCUMENTOS_VALIDADOS_DIR, id_tipo_documento)
    os.makedirs(carpeta_tipo, exist_ok=True)
    ruta_destino = os.path.join(carpeta_tipo, f"{id_documento}.pdf")
    shutil.copyfile(ruta_pdf, ruta_destino)
    return ruta_destino


def _registro_documento(id_documento, id_tipo_documento, nombre_archivo, ruta_archivo, campos, texto_ocr):
    return {
        "id_documento_validado": id_documento,
        "id_tipo_documento": id_tipo_documento,
        "nombre_archivo": nombre_archivo,
        "ruta_archivo": ruta_archivo,
        "campos_validados": campos,
        "texto_ocr": texto_ocr,
        "fecha_validacion": _fecha_actual(),
    }


def _actualizar_estado_lote(lote, estado):
    umbral = int(estado.get("configuracion", {}).get("umbral_lote", UMBRAL_LOTE_ENTRENAMIENTO))
    if len(lote.get("documentos", [])) >= umbral:
        lote["estado"] = "listo_para_entrenar"
    lote["documentos_acumulados"] = len(lote.get("documentos", []))


def _fecha_actual():
    return datetime.now(timezone.utc).isoformat()
