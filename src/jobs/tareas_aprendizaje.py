from src.jobs.celery_app import celery_app
from src.services.entrenador_lotes_aprendizaje import entrenar_y_evaluar_lote
from src.services.gestor_lotes_aprendizaje import (
    actualizar_lote,
    obtener_documentos_lote,
)
from src.services.gestor_tipos_documento import registrar_version_modelo


@celery_app.task(bind=True, name="aprendizaje.entrenar_lote", max_retries=1)
def entrenar_lote_aprendizaje(self, id_lote):
    try:
        return ejecutar_entrenamiento_lote(id_lote, self.request.id)
    except Exception as error:
        actualizar_lote(id_lote, estado="fallido", error=str(error))
        raise


def ejecutar_entrenamiento_lote(id_lote, id_tarea=None):
    actualizar_lote(id_lote, estado="entrenando", id_tarea=id_tarea)
    documentos = obtener_documentos_lote(id_lote)
    resultado = entrenar_y_evaluar_lote(id_lote, documentos)
    return finalizar_entrenamiento(id_lote, documentos, resultado)


def finalizar_entrenamiento(id_lote, documentos, resultado):
    estado_final = "activado" if resultado["decision"]["activar"] else "rechazado"
    version_modelo = registrar_modelo_si_aplica(documentos, id_lote, resultado)
    lote = actualizar_lote(
        id_lote,
        estado=estado_final,
        modelo_candidato=resultado["ruta_modelo"],
        metricas=resultado["metricas"],
        decision=resultado["decision"],
        recomendaciones=resultado["decision"].get("recomendaciones", []),
        version_modelo=version_modelo,
    )
    return {"id_lote": id_lote, "estado": lote["estado"], "decision": resultado["decision"]}


def registrar_modelo_si_aplica(documentos, id_lote, resultado):
    id_tipo_documento = documentos[0]["id_tipo_documento"]
    nombre_modelo = crear_nombre_modelo(id_tipo_documento, id_lote)
    return registrar_version_modelo(id_tipo_documento, crear_datos_modelo(nombre_modelo, resultado, len(documentos)))


def crear_nombre_modelo(id_tipo_documento, id_lote):
    return f"{id_tipo_documento}_{id_lote[:8]}"


def crear_datos_modelo(nombre_modelo, resultado, total_documentos):
    return {
        "nombre_modelo": nombre_modelo,
        "ruta_modelo": resultado["ruta_modelo"],
        "estado": "activo" if resultado["decision"]["activar"] else "rechazado",
        "documentos_entrenamiento": total_documentos,
        "metricas": crear_metricas_resumen(resultado["metricas"]),
        "observaciones": "; ".join(resultado["decision"].get("recomendaciones", [])),
        "activar": resultado["decision"]["activar"],
    }


def crear_metricas_resumen(metricas):
    campos = metricas.get("candidato", {})
    valores = [datos.get("f1", 0) for datos in campos.values()]
    f1 = round(sum(valores) / len(valores), 4) if valores else 0
    return {"f1_entidades": f1, "campos": campos}
