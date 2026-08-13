import hashlib
import json
import os
import secrets
from datetime import datetime, timezone

from config import API_KEYS_PATH


class ApiKeyInvalida(ValueError):
    """Indica que la API key no existe, esta inactiva o no tiene permisos."""


class ApiKeySolicitudInvalida(ValueError):
    """Indica que la solicitud para crear una API key no cumple los datos minimos."""


def cargar_catalogo_api_keys():
    if not os.path.exists(API_KEYS_PATH):
        return {"api_keys": []}

    with open(API_KEYS_PATH, "r", encoding="utf-8") as archivo:
        return json.load(archivo)


def guardar_catalogo_api_keys(catalogo):
    os.makedirs(os.path.dirname(API_KEYS_PATH), exist_ok=True)
    with open(API_KEYS_PATH, "w", encoding="utf-8") as archivo:
        json.dump(catalogo, archivo, ensure_ascii=False, indent=2)
        archivo.write("\n")


def calcular_hash_api_key(api_key):
    return hashlib.sha256(api_key.encode("utf-8")).hexdigest()


def enmascarar_api_key(api_key):
    return f"{api_key[:10]}...{api_key[-4:]}"


def listar_api_keys():
    catalogo = cargar_catalogo_api_keys()
    return [
        {
            "id_api_key": item["id_api_key"],
            "nombre": item["nombre"],
            "prefijo": item.get("prefijo", ""),
            "estado": item.get("estado", "activa"),
            "permisos": item.get("permisos", ["extract"]),
            "fecha_creacion": item.get("fecha_creacion"),
            "ultimo_uso": item.get("ultimo_uso"),
        }
        for item in catalogo.get("api_keys", [])
    ]


def existen_api_keys_activas():
    catalogo = cargar_catalogo_api_keys()
    return any(item.get("estado") == "activa" for item in catalogo.get("api_keys", []))


def generar_api_key(datos_api_key):
    nombre = (datos_api_key.get("nombre") or "").strip()
    if not nombre:
        raise ApiKeySolicitudInvalida("El nombre de la API key es obligatorio.")

    permisos = datos_api_key.get("permisos") or ["extract"]
    api_key = f"dp_{secrets.token_urlsafe(32)}"
    registro = {
        "id_api_key": secrets.token_hex(8),
        "nombre": nombre,
        "prefijo": enmascarar_api_key(api_key),
        "api_key_hash": calcular_hash_api_key(api_key),
        "estado": "activa",
        "permisos": permisos,
        "fecha_creacion": datetime.now(timezone.utc).isoformat(),
        "ultimo_uso": None,
    }

    catalogo = cargar_catalogo_api_keys()
    catalogo.setdefault("api_keys", []).append(registro)
    guardar_catalogo_api_keys(catalogo)

    respuesta = dict(registro)
    respuesta.pop("api_key_hash", None)
    return api_key, respuesta


def validar_api_key(api_key, permiso="extract"):
    if not existen_api_keys_activas():
        return True

    if not api_key:
        raise ApiKeyInvalida("API key requerida.")

    api_key_hash = calcular_hash_api_key(api_key)
    catalogo = cargar_catalogo_api_keys()
    for item in catalogo.get("api_keys", []):
        if item.get("api_key_hash") == api_key_hash and item.get("estado") == "activa":
            if permiso not in item.get("permisos", []):
                raise ApiKeyInvalida("La API key no tiene permiso para esta operacion.")
            item["ultimo_uso"] = datetime.now(timezone.utc).isoformat()
            guardar_catalogo_api_keys(catalogo)
            return True

    raise ApiKeyInvalida("API key invalida.")
