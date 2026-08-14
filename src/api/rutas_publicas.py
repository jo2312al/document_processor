import json

from flask import Blueprint, current_app, jsonify, redirect, render_template, request, url_for

from src.api.archivos import eliminar_si_existe, guardar_pdf_temporal, validar_pdf_subido
from src.api.autenticacion import (
    cerrar_sesion_admin,
    iniciar_sesion_admin,
    sesion_admin_activa,
    solicitud_cliente_no_autorizada,
    validar_credenciales_admin,
)
from src.api.respuestas import respuesta_error
from src.processors.predict import predecir_entidades
from src.services.despachador_tareas import despachar_entrenamiento_lote
from src.services.gestor_lotes_aprendizaje import (
    DocumentoValidadoInvalido,
    lote_listo_para_entrenar,
    registrar_documento_validado,
)
from src.services.gestor_preprocesamiento_documental import extraer_texto_documento
from src.services.gestor_tipos_documento import listar_tipos_documento

rutas_publicas = Blueprint("rutas_publicas", __name__)


@rutas_publicas.route("/", methods=["GET"])
@rutas_publicas.route("/analizador", methods=["GET"])
def mostrar_analizador():
    return render_template("analizador.html")


@rutas_publicas.route("/admin", methods=["GET"])
def mostrar_panel_admin():
    if not sesion_admin_activa():
        return redirect(url_for("rutas_publicas.mostrar_login"))
    return render_template("admin_panel.html")


@rutas_publicas.route("/login", methods=["GET", "POST"])
def mostrar_login():
    if request.method == "POST":
        return _procesar_login()
    return render_template("login.html", error=None)


@rutas_publicas.route("/logout", methods=["GET", "POST"])
def cerrar_login():
    cerrar_sesion_admin()
    return redirect(url_for("rutas_publicas.mostrar_login"))


@rutas_publicas.route("/tipos-documento", methods=["GET"])
def obtener_tipos_documento():
    return jsonify({"tipos_documento": _serializar_tipos_documento()}), 200


@rutas_publicas.route("/extract", methods=["POST"])
def extraer_datos_pdf():
    error_autorizacion = solicitud_cliente_no_autorizada()
    if error_autorizacion:
        return error_autorizacion
    archivo = request.files.get("file")
    error_archivo = validar_pdf_subido(archivo)
    if error_archivo:
        return respuesta_error(error_archivo, 400)
    return _procesar_pdf_subido(archivo)


@rutas_publicas.route("/aprendizaje/documentos-validados", methods=["POST"])
def recibir_documento_validado():
    error_autorizacion = solicitud_cliente_no_autorizada()
    if error_autorizacion:
        return error_autorizacion
    archivo = request.files.get("file")
    error_archivo = validar_pdf_subido(archivo)
    if error_archivo:
        return respuesta_error(error_archivo, 400)
    return _registrar_pdf_validado(archivo)


def _procesar_login():
    usuario = request.form.get("usuario", "")
    password = request.form.get("password", "")
    if validar_credenciales_admin(usuario, password):
        iniciar_sesion_admin(usuario)
        return redirect(url_for("rutas_publicas.mostrar_panel_admin"))
    return render_template("login.html", error="Usuario o contrasena incorrectos"), 401


def _registrar_pdf_validado(archivo):
    ruta_pdf, nombre_archivo = guardar_pdf_temporal(archivo, current_app.config["UPLOAD_FOLDER"], "validado")
    try:
        documento, lote = _crear_documento_validado(ruta_pdf, nombre_archivo)
        despacho = _despachar_si_lote_listo(lote)
        return jsonify(_respuesta_documento_validado(documento, lote, despacho)), 201
    except DocumentoValidadoInvalido as error:
        return respuesta_error(error, 400)
    finally:
        eliminar_si_existe(ruta_pdf)


def _crear_documento_validado(ruta_pdf, nombre_archivo):
    id_tipo = request.form.get("id_tipo_documento", "constancia_servicio")
    campos = _leer_campos_validados()
    texto_ocr = extraer_texto_documento(ruta_pdf).get("texto", "")
    return registrar_documento_validado(id_tipo, ruta_pdf, nombre_archivo, campos, texto_ocr)


def _leer_campos_validados():
    texto = request.form.get("campos_validados") or request.form.get("fields") or "{}"
    try:
        return json.loads(texto)
    except json.JSONDecodeError as error:
        raise DocumentoValidadoInvalido(f"campos_validados no es JSON valido: {error}")


def _despachar_si_lote_listo(lote):
    if lote_listo_para_entrenar(lote):
        return despachar_entrenamiento_lote(lote["id_lote"])
    return None


def _respuesta_documento_validado(documento, lote, despacho):
    return {
        "mensaje": "Documento validado recibido",
        "estado": "registrado_para_entrenamiento",
        "id_documento_validado": documento["id_documento_validado"],
        "id_lote": lote["id_lote"],
        "estado_lote": lote["estado"],
        "entrenamiento": despacho,
    }


def _serializar_tipos_documento():
    return [_serializar_tipo_documento(tipo) for tipo in listar_tipos_documento()]


def _serializar_tipo_documento(tipo):
    return {
        "id_tipo_documento": tipo["id_tipo_documento"],
        "nombre": tipo["nombre"],
        "descripcion": tipo.get("descripcion", ""),
        "estado": tipo.get("estado", "sin_estado"),
        "modelo_activo": tipo.get("modelo_activo"),
        "campos": tipo.get("campos", []),
        "rasgos_documento": tipo.get("rasgos_documento", {}),
        "versiones_modelo": tipo.get("versiones_modelo", []),
        "total_plantillas": len(tipo.get("plantillas", [])),
        "tiene_plantilla_activa": bool(tipo.get("plantilla_activa")),
    }


def _procesar_pdf_subido(archivo):
    ruta_pdf, _ = guardar_pdf_temporal(archivo, current_app.config["UPLOAD_FOLDER"], "extract")
    try:
        return jsonify(_extraer_con_modelo(ruta_pdf)), 200
    except Exception as error:
        current_app.logger.error("Error procesando PDF: %s", error)
        return respuesta_error(error, 500)
    finally:
        eliminar_si_existe(ruta_pdf)


def _extraer_con_modelo(ruta_pdf):
    return predecir_entidades(
        ruta_pdf,
        request.form.get("id_tipo_documento"),
        request.form.get("metodo_preprocesamiento"),
    )