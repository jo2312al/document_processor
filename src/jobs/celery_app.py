from celery import Celery

from config import CELERY_BROKER_URL, CELERY_RESULT_BACKEND, CELERY_TASK_ALWAYS_EAGER

celery_app = Celery("document_processor")
celery_app.conf.update(
    broker_url=CELERY_BROKER_URL,
    result_backend=CELERY_RESULT_BACKEND,
    task_always_eager=CELERY_TASK_ALWAYS_EAGER,
    task_time_limit=3600,
    task_soft_time_limit=3300,
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    worker_prefetch_multiplier=1,
    imports=("src.jobs.tareas_aprendizaje",),
)
