import json
import os
import re
from datetime import datetime, timezone
from functools import lru_cache

from config import (
    CATALOGO_DOCUMENTAL_BACKEND,
    MODELS_DIR,
    TIPO_DOCUMENTO_PREDETERMINADO,
    TIPOS_DOCUMENTO_PATH,
)


class TipoDocumentoNoEncontrado(ValueError):
    """Indica que el tipo documental solicitado no existe en el catalogo."""


class CatalogoDocumentoInvalido(ValueError):
    """Indica que una configuracion documental no cumple las reglas minimas."""


def usar_mysql():
    return CATALOGO_DOCUMENTAL_BACKEND == "mysql"


def obtener_repositorio_mysql():
    from src.repositories.catalogo_documental_mysql import CatalogoDocumentalMySQL

    return CatalogoDocumentalMySQL()


@lru_cache(maxsize=1)
def cargar_catalogo_tipos_documento():
    with open(TIPOS_DOCUMENTO_PATH, "r", encoding="utf-8") as archivo:
        return json.load(archivo)


def recargar_catalogo_tipos_documento():
    cargar_catalogo_tipos_documento.cache_clear()
    return cargar_catalogo_tipos_documento()


def guardar_catalogo_tipos_documento(catalogo):
    os.makedirs(os.path.dirname(TIPOS_DOCUMENTO_PATH), exist_ok=True)
    with open(TIPOS_DOCUMENTO_PATH, "w", encoding="utf-8") as archivo:
        json.dump(catalogo, archivo, ensure_ascii=False, indent=2)
        archivo.write("\n")
    recargar_catalogo_tipos_documento()


def generar_id_texto(texto):
    texto_normalizado = texto.strip().lower()
    for origen, destino in _reemplazos_acentos().items():
        texto_normalizado = texto_normalizado.replace(origen, destino)
    texto_normalizado = re.sub(r"[^a-z0-9]+", "_", texto_normalizado)
    return texto_normalizado.strip("_") or "tipo_documento"


def listar_tipos_documento():
    if usar_mysql():
        return obtener_repositorio_mysql().listar_tipos_documento()
    return cargar_catalogo_tipos_documento().get("tipos_documento", [])


def obtener_tipo_documento(id_tipo_documento=None):
    if usar_mysql():
        return _obtener_tipo_mysql(id_tipo_documento)
    return _obtener_tipo_json(id_tipo_documento)


def obtener_ruta_modelo_activo(tipo_documento):
    nombre_modelo = tipo_documento.get("modelo_activo")
    if not nombre_modelo:
        raise ValueError("El tipo de documento no tiene un modelo activo configurado.")
    if os.path.isabs(nombre_modelo):
        return nombre_modelo
    return os.path.join(MODELS_DIR, nombre_modelo)


def construir_campos_extraidos(tipo_documento, entidades_detectadas):
    campos = {}
    faltantes = []
    for campo in tipo_documento.get("campos", []):
        valor = entidades_detectadas.get(campo["etiqueta_entidad"], "NO ENCONTRADO")
        campos[campo["clave"]] = _construir_campo_extraido(campo, valor)
        if campo.get("obligatorio") and valor == "NO ENCONTRADO":
            faltantes.append(campo["clave"])
    return campos, faltantes


def normalizar_tipo_documento(datos_tipo_documento):
    nombre = (datos_tipo_documento.get("nombre") or "").strip()
    if not nombre:
        raise CatalogoDocumentoInvalido("El nombre del tipo de documento es obligatorio.")
    return _crear_tipo_normalizado(datos_tipo_documento, nombre)


def crear_tipo_documento(datos_tipo_documento):
    tipo_documento = normalizar_tipo_documento(datos_tipo_documento)
    if usar_mysql():
        return obtener_repositorio_mysql().crear_tipo_documento(tipo_documento)
    _validar_tipo_no_duplicado(tipo_documento["id_tipo_documento"])
    return _guardar_tipo_json(tipo_documento)


def normalizar_campo_documento(datos_campo):
    nombre = (datos_campo.get("nombre") or "").strip()
    etiqueta = (datos_campo.get("etiqueta_entidad") or "").strip().upper()
    if not nombre or not etiqueta:
        raise CatalogoDocumentoInvalido("El nombre y la etiqueta de entidad son obligatorios.")
    return _crear_campo_normalizado(datos_campo, nombre, etiqueta)


def agregar_campo_documento(id_tipo_documento, datos_campo):
    campo = normalizar_campo_documento(datos_campo)
    if usar_mysql():
        return _agregar_campo_mysql(id_tipo_documento, campo)
    tipo_documento = _buscar_tipo_en_catalogo(id_tipo_documento)
    _validar_campo_no_duplicado(tipo_documento, campo["clave"])
    tipo_documento.setdefault("campos", []).append(campo)
    guardar_catalogo_tipos_documento(cargar_catalogo_tipos_documento())
    return campo


def normalizar_version_modelo(datos_modelo):
    nombre_modelo = (datos_modelo.get("nombre_modelo") or "").strip()
    if not nombre_modelo:
        raise CatalogoDocumentoInvalido("El nombre del modelo es obligatorio.")
    return _crear_version_normalizada(datos_modelo, nombre_modelo)


def registrar_version_modelo(id_tipo_documento, datos_modelo):
    version_modelo = normalizar_version_modelo(datos_modelo)
    if usar_mysql():
        return _registrar_version_mysql(id_tipo_documento, version_modelo)
    tipo_documento = _buscar_tipo_en_catalogo(id_tipo_documento)
    _agregar_version_json(tipo_documento, version_modelo)
    guardar_catalogo_tipos_documento(cargar_catalogo_tipos_documento())
    return version_modelo


def obtener_version_modelo(tipo_documento, nombre_modelo):
    for version in tipo_documento.get("versiones_modelo", []):
        if version.get("nombre_modelo") == nombre_modelo:
            return version
    raise CatalogoDocumentoInvalido(f"No existe la version de modelo: {nombre_modelo}")


def puntaje_version_modelo(version_modelo):
    metricas = version_modelo.get("metricas", {})
    return float(metricas.get("f1_entidades") or metricas.get("f1") or 0)


def comparar_versiones_modelo(id_tipo_documento, nombre_modelo_candidato):
    tipo_documento = obtener_tipo_documento(id_tipo_documento)
    version_activa = obtener_version_modelo(tipo_documento, tipo_documento.get("modelo_activo"))
    version_candidata = obtener_version_modelo(tipo_documento, nombre_modelo_candidato)
    return construir_comparacion_modelos(version_activa, version_candidata)


def construir_comparacion_modelos(version_activa, version_candidata):
    puntaje_activo = puntaje_version_modelo(version_activa)
    puntaje_candidato = puntaje_version_modelo(version_candidata)
    return {
        "modelo_activo": version_activa.get("nombre_modelo"),
        "modelo_candidato": version_candidata.get("nombre_modelo"),
        "puntaje_activo": puntaje_activo,
        "puntaje_candidato": puntaje_candidato,
        "mejora": round(puntaje_candidato - puntaje_activo, 4),
        "recomendacion": "activar" if puntaje_candidato > puntaje_activo else "conservar_actual",
    }


def _reemplazos_acentos():
    return {"á": "a", "é": "e", "í": "i", "ó": "o", "ú": "u", "ñ": "n", "ü": "u"}


def _obtener_tipo_mysql(id_tipo_documento):
    id_solicitado = id_tipo_documento or TIPO_DOCUMENTO_PREDETERMINADO
    tipo_documento = obtener_repositorio_mysql().obtener_tipo_documento(id_solicitado)
    if tipo_documento:
        return tipo_documento
    raise TipoDocumentoNoEncontrado(f"No existe configuracion para el tipo de documento: {id_solicitado}")


def _obtener_tipo_json(id_tipo_documento):
    catalogo = cargar_catalogo_tipos_documento()
    id_solicitado = id_tipo_documento or catalogo.get("tipo_documento_predeterminado")
    return _buscar_tipo_en_catalogo(id_solicitado or TIPO_DOCUMENTO_PREDETERMINADO)


def _buscar_tipo_en_catalogo(id_tipo_documento):
    for tipo_documento in cargar_catalogo_tipos_documento().get("tipos_documento", []):
        if tipo_documento.get("id_tipo_documento") == id_tipo_documento:
            return tipo_documento
    raise TipoDocumentoNoEncontrado(f"No existe configuracion para el tipo de documento: {id_tipo_documento}")


def _construir_campo_extraido(campo, valor):
    return {
        "nombre": campo.get("nombre", campo["clave"]),
        "etiqueta_entidad": campo["etiqueta_entidad"],
        "value": valor,
        "obligatorio": bool(campo.get("obligatorio", False)),
    }


def _crear_tipo_normalizado(datos, nombre):
    return {
        "id_tipo_documento": datos.get("id_tipo_documento") or generar_id_texto(nombre),
        "nombre": nombre,
        "descripcion": datos.get("descripcion", ""),
        "modelo_activo": datos.get("modelo_activo", "spacy_model"),
        "estado": datos.get("estado", "borrador"),
        "campos": datos.get("campos", []),
        "rasgos_documento": _rasgos_predeterminados(datos),
        "preprocesamiento": datos.get("preprocesamiento", {"metodo": "tesseract", "permitir_docling": True}),
        "versiones_modelo": datos.get("versiones_modelo", []),
        "fecha_creacion": datetime.now(timezone.utc).isoformat(),
    }


def _rasgos_predeterminados(datos):
    return datos.get("rasgos_documento", {"palabras_clave": [], "paginas_esperadas": None, "origen": "escaneado_o_digital"})


def _validar_tipo_no_duplicado(id_tipo_documento):
    tipos = cargar_catalogo_tipos_documento().get("tipos_documento", [])
    if any(tipo.get("id_tipo_documento") == id_tipo_documento for tipo in tipos):
        raise CatalogoDocumentoInvalido(f"Ya existe el tipo de documento: {id_tipo_documento}")


def _guardar_tipo_json(tipo_documento):
    catalogo = cargar_catalogo_tipos_documento()
    catalogo.setdefault("tipos_documento", []).append(tipo_documento)
    guardar_catalogo_tipos_documento(catalogo)
    return tipo_documento


def _crear_campo_normalizado(datos, nombre, etiqueta):
    return {
        "clave": datos.get("clave") or generar_id_texto(nombre),
        "nombre": nombre,
        "etiqueta_entidad": etiqueta,
        "obligatorio": bool(datos.get("obligatorio", False)),
        "tipo_dato": datos.get("tipo_dato", "texto"),
        "descripcion": datos.get("descripcion", ""),
        "expresion_validacion": datos.get("expresion_validacion"),
        "orden_visualizacion": int(datos.get("orden_visualizacion", 0)),
    }


def _agregar_campo_mysql(id_tipo_documento, campo):
    campo_creado = obtener_repositorio_mysql().agregar_campo_documento(id_tipo_documento, campo)
    if campo_creado is None:
        raise TipoDocumentoNoEncontrado(f"No existe configuracion para el tipo de documento: {id_tipo_documento}")
    return campo_creado


def _validar_campo_no_duplicado(tipo_documento, clave_campo):
    campos = tipo_documento.setdefault("campos", [])
    if any(campo.get("clave") == clave_campo for campo in campos):
        raise CatalogoDocumentoInvalido(f"Ya existe el campo: {clave_campo}")


def _crear_version_normalizada(datos, nombre_modelo):
    return {
        "nombre_modelo": nombre_modelo,
        "ruta_modelo": datos.get("ruta_modelo", os.path.join(MODELS_DIR, nombre_modelo)),
        "estado": datos.get("estado", "pruebas"),
        "documentos_entrenamiento": int(datos.get("documentos_entrenamiento", 0)),
        "metricas": datos.get("metricas", {}),
        "observaciones": datos.get("observaciones", ""),
        "activar": bool(datos.get("activar", False)),
        "fecha_registro": datetime.now(timezone.utc).isoformat(),
    }


def _registrar_version_mysql(id_tipo_documento, version_modelo):
    version_creada = obtener_repositorio_mysql().registrar_version_modelo(id_tipo_documento, version_modelo)
    if version_creada is None:
        raise TipoDocumentoNoEncontrado(f"No existe configuracion para el tipo de documento: {id_tipo_documento}")
    return version_creada


def _agregar_version_json(tipo_documento, version_modelo):
    tipo_documento.setdefault("versiones_modelo", []).append(version_modelo)
    if version_modelo.get("activar") is True:
        tipo_documento["modelo_activo"] = version_modelo["nombre_modelo"]
        version_modelo["estado"] = "activo"
