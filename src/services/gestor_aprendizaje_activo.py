import json
import os
import uuid
from datetime import datetime, timezone

from config import APRENDIZAJE_ACTIVO_PATH


def cargar_cola_aprendizaje():
    if not os.path.exists(APRENDIZAJE_ACTIVO_PATH):
        return {"eventos": []}
    with open(APRENDIZAJE_ACTIVO_PATH, "r", encoding="utf-8") as archivo:
        return json.load(archivo)


def guardar_cola_aprendizaje(cola):
    os.makedirs(os.path.dirname(APRENDIZAJE_ACTIVO_PATH), exist_ok=True)
    with open(APRENDIZAJE_ACTIVO_PATH, "w", encoding="utf-8") as archivo:
        json.dump(cola, archivo, ensure_ascii=False, indent=2)
        archivo.write("\n")


def confianza_campo(campo):
    valor = campo.get("value")
    return 0.0 if valor in (None, "", "NO ENCONTRADO") else 0.85


def calcular_confianza_campos(campos_extraidos):
    valores = [confianza_campo(campo) for campo in campos_extraidos.values()]
    return round(sum(valores) / len(valores), 4) if valores else 0


def detectar_motivo_revision(campos_faltantes, confianza_global):
    if campos_faltantes:
        return "campos_obligatorios_faltantes"
    if confianza_global < 0.70:
        return "confianza_baja"
    return None


def construir_evento(id_tipo_documento, nombre_archivo, resultado, motivo):
    return {
        "id_evento": str(uuid.uuid4()),
        "id_tipo_documento": id_tipo_documento,
        "nombre_archivo": nombre_archivo,
        "motivo": motivo,
        "estado": "pendiente",
        "confianza_global": resultado.get("confianza_global", 0),
        "campos_faltantes": resultado.get("campos_faltantes", []),
        "fecha_registro": datetime.now(timezone.utc).isoformat(),
    }


def crear_evento_revision(id_tipo_documento, nombre_archivo, resultado, motivo):
    evento = construir_evento(id_tipo_documento, nombre_archivo, resultado, motivo)
    cola = cargar_cola_aprendizaje()
    cola.setdefault("eventos", []).append(evento)
    guardar_cola_aprendizaje(cola)
    return evento


def listar_eventos_revision(id_tipo_documento=None):
    eventos = cargar_cola_aprendizaje().get("eventos", [])
    if not id_tipo_documento:
        return eventos
    return [evento for evento in eventos if evento.get("id_tipo_documento") == id_tipo_documento]


def registrar_revision_si_aplica(id_tipo_documento, nombre_archivo, resultado):
    faltantes = resultado.get("campos_faltantes", [])
    motivo = detectar_motivo_revision(faltantes, resultado["confianza_global"])
    return crear_evento_revision(id_tipo_documento, nombre_archivo, resultado, motivo) if motivo else None
