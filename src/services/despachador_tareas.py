from celery.exceptions import CeleryError
from kombu.exceptions import OperationalError

from src.jobs.tareas_aprendizaje import entrenar_lote_aprendizaje, ejecutar_entrenamiento_lote
from src.services.gestor_lotes_aprendizaje import marcar_lote_en_cola


def despachar_entrenamiento_lote(id_lote):
    try:
        tarea = entrenar_lote_aprendizaje.delay(id_lote)
        marcar_lote_en_cola(id_lote, tarea.id)
        return {"modo": "celery", "id_tarea": tarea.id}
    except (OperationalError, CeleryError, ConnectionError):
        resultado = ejecutar_entrenamiento_lote(id_lote, "local")
        return {"modo": "local", "resultado": resultado}
