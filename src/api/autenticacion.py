import hmac

from flask import jsonify, request, session

from config import ADMIN_API_TOKEN, ADMIN_PASSWORD, ADMIN_USERNAME
from src.services.gestor_api_keys import ApiKeyInvalida, validar_api_key


def solicitud_admin_no_autorizada():
    if validar_admin_autenticado():
        return None
    return jsonify({"error": "Operacion administrativa no autorizada"}), 401


def validar_admin_autenticado():
    return sesion_admin_activa() or validar_token_administrador()


def sesion_admin_activa():
    return session.get("admin_autenticado") is True


def validar_credenciales_admin(usuario, password):
    if not ADMIN_PASSWORD:
        return False
    usuario_valido = hmac.compare_digest(usuario or "", ADMIN_USERNAME or "")
    password_valido = hmac.compare_digest(password or "", ADMIN_PASSWORD or "")
    return usuario_valido and password_valido


def iniciar_sesion_admin(usuario):
    session.clear()
    session["admin_autenticado"] = True
    session["admin_usuario"] = usuario


def cerrar_sesion_admin():
    session.clear()


def validar_token_administrador():
    if not ADMIN_API_TOKEN:
        return False
    return hmac.compare_digest(request.headers.get("X-Admin-Token", ""), ADMIN_API_TOKEN)


def obtener_api_key_solicitud():
    encabezado = request.headers.get("Authorization", "")
    if encabezado.lower().startswith("bearer "):
        return encabezado.split(" ", 1)[1].strip()
    return request.headers.get("X-API-Key")


def solicitud_cliente_no_autorizada():
    try:
        validar_api_key(obtener_api_key_solicitud(), permiso="extract")
        return None
    except ApiKeyInvalida as error:
        return jsonify({"error": str(error)}), 401