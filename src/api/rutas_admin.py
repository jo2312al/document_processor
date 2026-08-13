from flask import Blueprint, current_app, jsonify, request

from src.api.archivos import eliminar_si_existe, guardar_pdf_temporal, validar_pdf_subido
from src.api.autenticacion import solicitud_admin_no_autorizada
from src.api.respuestas import respuesta_error, respuesta_json, respuesta_lista
from src.services.despachador_tareas import despachar_entrenamiento_lote
from src.services.gestor_aprendizaje_activo import listar_eventos_revision
from src.services.gestor_api_keys import ApiKeySolicitudInvalida, generar_api_key, listar_api_keys
from src.services.gestor_entrenamiento_documentos import (
    DocumentoEntrenamientoInvalido,
    DocumentoEntrenamientoNoEncontrado,
    agregar_anotacion_entrenamiento,
    crear_documento_entrenamiento,
    listar_documentos_entrenamiento,
)
from src.services.gestor_lotes_aprendizaje import (
    LoteAprendizajeNoEncontrado,
    listar_lotes_aprendizaje,
)
from src.services.gestor_plantillas_documento import (
    PlantillaDocumentoInvalida,
    crear_plantilla_desde_pdf,
)
from src.services.gestor_preprocesamiento_documental import extraer_texto_documento
from src.services.gestor_tipos_documento import (
    CatalogoDocumentoInvalido,
    TipoDocumentoNoEncontrado,
    agregar_campo_documento,
    comparar_versiones_modelo,
    crear_tipo_documento,
    registrar_version_modelo,
)

rutas_admin = Blueprint("rutas_admin", __name__, url_prefix="/admin")


@rutas_admin.before_request
def validar_solicitud_admin():
    return solicitud_admin_no_autorizada()


@rutas_admin.route("/tipos-documento", methods=["POST"])
def registrar_tipo_documento():
    return _ejecutar_creacion(crear_tipo_documento, "tipo_documento")


@rutas_admin.route("/tipos-documento/<id_tipo_documento>/campos", methods=["POST"])
def registrar_campo_documento(id_tipo_documento):
    return _ejecutar_con_tipo(agregar_campo_documento, id_tipo_documento, "campo")


@rutas_admin.route("/tipos-documento/<id_tipo_documento>/modelos", methods=["POST"])
def registrar_modelo_documento(id_tipo_documento):
    return _ejecutar_con_tipo(registrar_version_modelo, id_tipo_documento, "version_modelo")


@rutas_admin.route("/tipos-documento/<id_tipo_documento>/modelos/comparar", methods=["GET"])
def comparar_modelo_documento(id_tipo_documento):
    nombre_modelo = request.args.get("modelo_candidato")
    if not nombre_modelo:
        return respuesta_error("modelo_candidato es obligatorio", 400)
    return _comparar_modelos(id_tipo_documento, nombre_modelo)


@rutas_admin.route("/tipos-documento/<id_tipo_documento>/documentos-entrenamiento", methods=["GET"])
def obtener_documentos_entrenamiento(id_tipo_documento):
    return respuesta_lista("documentos_entrenamiento", listar_documentos_entrenamiento(id_tipo_documento))


@rutas_admin.route("/tipos-documento/<id_tipo_documento>/aprendizaje-activo", methods=["GET"])
def obtener_eventos_aprendizaje_activo(id_tipo_documento):
    return respuesta_lista("eventos_revision", listar_eventos_revision(id_tipo_documento))


@rutas_admin.route("/tipos-documento/<id_tipo_documento>/documentos-entrenamiento", methods=["POST"])
def subir_documento_entrenamiento(id_tipo_documento):
    archivo = request.files.get("file")
    error_archivo = validar_pdf_subido(archivo)
    if error_archivo:
        return respuesta_error(error_archivo, 400)
    return _crear_documento_desde_pdf(id_tipo_documento, archivo)


@rutas_admin.route("/tipos-documento/<id_tipo_documento>/plantillas", methods=["POST"])
def crear_plantilla_documento(id_tipo_documento):
    archivo = request.files.get("file")
    error_archivo = validar_pdf_subido(archivo)
    if error_archivo:
        return respuesta_error(error_archivo, 400)
    return _crear_plantilla_desde_pdf(id_tipo_documento, archivo)


@rutas_admin.route("/documentos-entrenamiento/<id_documento>/anotaciones", methods=["POST"])
def registrar_anotacion_documento(id_documento):
    return _registrar_anotacion(id_documento, request.get_json(silent=True) or {})


@rutas_admin.route("/api-keys", methods=["GET"])
def obtener_api_keys():
    return respuesta_lista("api_keys", listar_api_keys())


@rutas_admin.route("/api-keys", methods=["POST"])
def crear_api_key():
    try:
        api_key, registro = generar_api_key(request.get_json(silent=True) or {})
        return jsonify({"api_key": api_key, "registro": registro}), 201
    except ApiKeySolicitudInvalida as error:
        return respuesta_error(error, 400)


@rutas_admin.route("/aprendizaje/lotes", methods=["GET"])
def obtener_lotes_aprendizaje():
    id_tipo = request.args.get("id_tipo_documento")
    return respuesta_json("aprendizaje", listar_lotes_aprendizaje(id_tipo))


@rutas_admin.route("/aprendizaje/lotes/<id_lote>/entrenar", methods=["POST"])
def entrenar_lote_manual(id_lote):
    try:
        return respuesta_json("entrenamiento", despachar_entrenamiento_lote(id_lote), 202)
    except LoteAprendizajeNoEncontrado as error:
        return respuesta_error(error, 404)
    except Exception as error:
        return respuesta_error(error, 500)


def _ejecutar_creacion(funcion_servicio, clave_respuesta):
    try:
        return respuesta_json(clave_respuesta, funcion_servicio(request.get_json(silent=True) or {}), 201)
    except CatalogoDocumentoInvalido as error:
        return respuesta_error(error, 400)


def _ejecutar_con_tipo(funcion_servicio, id_tipo_documento, clave_respuesta):
    try:
        resultado = funcion_servicio(id_tipo_documento, request.get_json(silent=True) or {})
        return respuesta_json(clave_respuesta, resultado, 201)
    except TipoDocumentoNoEncontrado as error:
        return respuesta_error(error, 404)
    except CatalogoDocumentoInvalido as error:
        return respuesta_error(error, 400)


def _comparar_modelos(id_tipo_documento, nombre_modelo):
    try:
        return respuesta_json("comparacion", comparar_versiones_modelo(id_tipo_documento, nombre_modelo))
    except Exception as error:
        return respuesta_error(error, 400)


def _crear_documento_desde_pdf(id_tipo_documento, archivo):
    ruta_pdf, nombre_archivo = guardar_pdf_temporal(archivo, current_app.config["UPLOAD_FOLDER"], "training")
    try:
        texto_ocr = _extraer_texto_entrenamiento(ruta_pdf)
        documento = crear_documento_entrenamiento(id_tipo_documento, ruta_pdf, nombre_archivo, texto_ocr)
        return respuesta_json("documento_entrenamiento", documento, 201)
    except DocumentoEntrenamientoInvalido as error:
        return respuesta_error(error, 400)
    finally:
        eliminar_si_existe(ruta_pdf)


def _crear_plantilla_desde_pdf(id_tipo_documento, archivo):
    ruta_pdf, _ = guardar_pdf_temporal(archivo, current_app.config["UPLOAD_FOLDER"], "plantilla")
    try:
        datos = _leer_datos_plantilla()
        plantilla = crear_plantilla_desde_pdf(id_tipo_documento, ruta_pdf, datos)
        return respuesta_json("plantilla", plantilla, 201)
    except (CatalogoDocumentoInvalido, PlantillaDocumentoInvalida, ValueError) as error:
        return respuesta_error(error, 400)
    finally:
        eliminar_si_existe(ruta_pdf)


def _leer_datos_plantilla():
    return {
        "nombre_plantilla": request.form.get("nombre_plantilla"),
        "campos_muestra": request.form.get("campos_muestra"),
    }


def _extraer_texto_entrenamiento(ruta_pdf):
    resultado = extraer_texto_documento(ruta_pdf, metodo_solicitado=request.form.get("metodo_preprocesamiento"))
    return resultado.get("texto", "")


def _registrar_anotacion(id_documento, datos):
    try:
        return respuesta_json("anotacion", agregar_anotacion_entrenamiento(id_documento, datos), 201)
    except DocumentoEntrenamientoNoEncontrado as error:
        return respuesta_error(error, 404)
    except DocumentoEntrenamientoInvalido as error:
        return respuesta_error(error, 400)