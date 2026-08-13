from flask import Blueprint, current_app, jsonify, render_template, request

from src.api.archivos import eliminar_si_existe, guardar_pdf_temporal, validar_pdf_subido
from src.api.autenticacion import solicitud_cliente_no_autorizada
from src.api.respuestas import respuesta_error
from src.processors.predict import predecir_entidades
from src.services.gestor_tipos_documento import listar_tipos_documento

rutas_publicas = Blueprint("rutas_publicas", __name__)


@rutas_publicas.route("/", methods=["GET"])
def mostrar_analizador():
    return render_template("analizador.html")


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
    }


def _procesar_pdf_subido(archivo):
    ruta_pdf, _ = guardar_pdf_temporal(archivo, current_app.config["UPLOAD_FOLDER"], "extract")
    try:
        resultado = _extraer_con_modelo(ruta_pdf)
        return jsonify(resultado), 200
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
