from flask import jsonify, request

from config import ADMIN_API_TOKEN
from src.services.gestor_api_keys import ApiKeyInvalida, validar_api_key


def solicitud_admin_no_autorizada():
    if validar_token_administrador():
        return None
    return jsonify({"error": "Operacion administrativa no autorizada"}), 401


def validar_token_administrador():
    if not ADMIN_API_TOKEN:
        return False
    return request.headers.get("X-Admin-Token") == ADMIN_API_TOKEN


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
