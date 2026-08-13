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
    reemplazos = {
        "Ã¡": "a",
        "Ã©": "e",
        "Ã­": "i",
        "Ã³": "o",
        "Ãº": "u",
        "Ã±": "n",
        "Ã¼": "u",
    }
    for origen, destino in reemplazos.items():
        texto_normalizado = texto_normalizado.replace(origen, destino)

    texto_normalizado = re.sub(r"[^a-z0-9]+", "_", texto_normalizado)
    texto_normalizado = texto_normalizado.strip("_")
    return texto_normalizado or "tipo_documento"


def listar_tipos_documento():
    if usar_mysql():
        return obtener_repositorio_mysql().listar_tipos_documento()

    catalogo = cargar_catalogo_tipos_documento()
    return catalogo.get("tipos_documento", [])


def obtener_tipo_documento(id_tipo_documento=None):
    id_solicitado = id_tipo_documento or TIPO_DOCUMENTO_PREDETERMINADO

    if usar_mysql():
        tipo_documento = obtener_repositorio_mysql().obtener_tipo_documento(id_solicitado)
        if tipo_documento:
            return tipo_documento
        raise TipoDocumentoNoEncontrado(
            f"No existe configuracion para el tipo de documento: {id_solicitado}"
        )

    catalogo = cargar_catalogo_tipos_documento()
    id_solicitado = id_tipo_documento or catalogo.get(
        "tipo_documento_predeterminado",
        TIPO_DOCUMENTO_PREDETERMINADO,
    )

    for tipo_documento in catalogo.get("tipos_documento", []):
        if tipo_documento.get("id_tipo_documento") == id_solicitado:
            return tipo_documento

    raise TipoDocumentoNoEncontrado(
        f"No existe configuracion para el tipo de documento: {id_solicitado}"
    )


def obtener_ruta_modelo_activo(tipo_documento):
    nombre_modelo = tipo_documento.get("modelo_activo")
    if not nombre_modelo:
        raise ValueError("El tipo de documento no tiene un modelo activo configurado.")

    if os.path.isabs(nombre_modelo):
        return nombre_modelo

    return os.path.join(MODELS_DIR, nombre_modelo)


def construir_campos_extraidos(tipo_documento, entidades_detectadas):
    campos_extraidos = {}
    campos_faltantes = []

    for campo in tipo_documento.get("campos", []):
        clave = campo["clave"]
        etiqueta = campo["etiqueta_entidad"]
        valor = entidades_detectadas.get(etiqueta, "NO ENCONTRADO")

        campos_extraidos[clave] = {
            "nombre": campo.get("nombre", clave),
            "etiqueta_entidad": etiqueta,
            "value": valor,
            "obligatorio": bool(campo.get("obligatorio", False)),
        }

        if campo.get("obligatorio") and valor == "NO ENCONTRADO":
            campos_faltantes.append(clave)

    return campos_extraidos, campos_faltantes


def normalizar_tipo_documento(datos_tipo_documento):
    nombre = (datos_tipo_documento.get("nombre") or "").strip()
    if not nombre:
        raise CatalogoDocumentoInvalido("El nombre del tipo de documento es obligatorio.")

    id_tipo_documento = datos_tipo_documento.get("id_tipo_documento") or generar_id_texto(nombre)
    return {
        "id_tipo_documento": id_tipo_documento,
        "nombre": nombre,
        "descripcion": datos_tipo_documento.get("descripcion", ""),
        "modelo_activo": datos_tipo_documento.get("modelo_activo", "spacy_model"),
        "estado": datos_tipo_documento.get("estado", "borrador"),
        "campos": datos_tipo_documento.get("campos", []),
        "rasgos_documento": datos_tipo_documento.get(
            "rasgos_documento",
            {
                "palabras_clave": [],
                "paginas_esperadas": None,
                "origen": "escaneado_o_digital",
            },
        ),
        "preprocesamiento": datos_tipo_documento.get(
            "preprocesamiento",
            {"metodo": "tesseract", "permitir_docling": True},
        ),
        "versiones_modelo": datos_tipo_documento.get("versiones_modelo", []),
        "fecha_creacion": datetime.now(timezone.utc).isoformat(),
    }


def crear_tipo_documento(datos_tipo_documento):
    tipo_documento = normalizar_tipo_documento(datos_tipo_documento)

    if usar_mysql():
        return obtener_repositorio_mysql().crear_tipo_documento(tipo_documento)

    catalogo = cargar_catalogo_tipos_documento()
    tipos_documento = catalogo.setdefault("tipos_documento", [])

    if any(
        tipo.get("id_tipo_documento") == tipo_documento["id_tipo_documento"]
        for tipo in tipos_documento
    ):
        raise CatalogoDocumentoInvalido(
            f"Ya existe el tipo de documento: {tipo_documento['id_tipo_documento']}"
        )

    tipos_documento.append(tipo_documento)
    guardar_catalogo_tipos_documento(catalogo)
    return tipo_documento


def normalizar_campo_documento(datos_campo):
    nombre = (datos_campo.get("nombre") or "").strip()
    etiqueta_entidad = (datos_campo.get("etiqueta_entidad") or "").strip().upper()
    if not nombre or not etiqueta_entidad:
        raise CatalogoDocumentoInvalido("El nombre y la etiqueta de entidad son obligatorios.")

    return {
        "clave": datos_campo.get("clave") or generar_id_texto(nombre),
        "nombre": nombre,
        "etiqueta_entidad": etiqueta_entidad,
        "obligatorio": bool(datos_campo.get("obligatorio", False)),
        "tipo_dato": datos_campo.get("tipo_dato", "texto"),
        "descripcion": datos_campo.get("descripcion", ""),
        "expresion_validacion": datos_campo.get("expresion_validacion"),
        "orden_visualizacion": int(datos_campo.get("orden_visualizacion", 0)),
    }


def agregar_campo_documento(id_tipo_documento, datos_campo):
    campo = normalizar_campo_documento(datos_campo)

    if usar_mysql():
        campo_creado = obtener_repositorio_mysql().agregar_campo_documento(
            id_tipo_documento,
            campo,
        )
        if campo_creado is None:
            raise TipoDocumentoNoEncontrado(
                f"No existe configuracion para el tipo de documento: {id_tipo_documento}"
            )
        return campo_creado

    catalogo = cargar_catalogo_tipos_documento()
    tipo_documento = None
    for tipo in catalogo.get("tipos_documento", []):
        if tipo.get("id_tipo_documento") == id_tipo_documento:
            tipo_documento = tipo
            break

    if tipo_documento is None:
        raise TipoDocumentoNoEncontrado(
            f"No existe configuracion para el tipo de documento: {id_tipo_documento}"
        )

    campos = tipo_documento.setdefault("campos", [])
    if any(campo_existente.get("clave") == campo["clave"] for campo_existente in campos):
        raise CatalogoDocumentoInvalido(f"Ya existe el campo: {campo['clave']}")

    campos.append(campo)
    guardar_catalogo_tipos_documento(catalogo)
    return campo


def normalizar_version_modelo(datos_modelo):
    nombre_modelo = (datos_modelo.get("nombre_modelo") or "").strip()
    if not nombre_modelo:
        raise CatalogoDocumentoInvalido("El nombre del modelo es obligatorio.")

    return {
        "nombre_modelo": nombre_modelo,
        "ruta_modelo": datos_modelo.get("ruta_modelo", os.path.join(MODELS_DIR, nombre_modelo)),
        "estado": datos_modelo.get("estado", "pruebas"),
        "documentos_entrenamiento": int(datos_modelo.get("documentos_entrenamiento", 0)),
        "metricas": datos_modelo.get("metricas", {}),
        "observaciones": datos_modelo.get("observaciones", ""),
        "activar": bool(datos_modelo.get("activar", False)),
        "fecha_registro": datetime.now(timezone.utc).isoformat(),
    }


def registrar_version_modelo(id_tipo_documento, datos_modelo):
    version_modelo = normalizar_version_modelo(datos_modelo)

    if usar_mysql():
        version_creada = obtener_repositorio_mysql().registrar_version_modelo(
            id_tipo_documento,
            version_modelo,
        )
        if version_creada is None:
            raise TipoDocumentoNoEncontrado(
                f"No existe configuracion para el tipo de documento: {id_tipo_documento}"
            )
        return version_creada

    catalogo = cargar_catalogo_tipos_documento()
    tipo_documento = None
    for tipo in catalogo.get("tipos_documento", []):
        if tipo.get("id_tipo_documento") == id_tipo_documento:
            tipo_documento = tipo
            break

    if tipo_documento is None:
        raise TipoDocumentoNoEncontrado(
            f"No existe configuracion para el tipo de documento: {id_tipo_documento}"
        )

    tipo_documento.setdefault("versiones_modelo", []).append(version_modelo)
    if version_modelo.get("activar") is True:
        tipo_documento["modelo_activo"] = version_modelo["nombre_modelo"]
        version_modelo["estado"] = "activo"

    guardar_catalogo_tipos_documento(catalogo)
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
    modelo_activo = tipo_documento.get("modelo_activo")
    version_activa = obtener_version_modelo(tipo_documento, modelo_activo)
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
