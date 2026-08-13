import logging
import os
import tempfile

from flask import Flask

from config import LOGGING_FORMAT, LOGGING_LEVEL, LOGS_DIR
from src.api.rutas_admin import rutas_admin
from src.api.rutas_publicas import rutas_publicas


def crear_aplicacion():
    app = Flask(__name__, template_folder=_ruta_plantillas())
    configurar_carga_archivos(app)
    configurar_registro_eventos()
    registrar_rutas(app)
    return app


def _ruta_plantillas():
    base = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    return os.path.join(base, "templates")


def configurar_carga_archivos(app):
    app.config["UPLOAD_FOLDER"] = tempfile.gettempdir()
    app.config["MAX_CONTENT_LENGTH"] = 16 * 1024 * 1024


def configurar_registro_eventos():
    os.makedirs(LOGS_DIR, exist_ok=True)
    logging.basicConfig(
        filename=os.path.join(LOGS_DIR, "api.log"),
        level=getattr(logging, LOGGING_LEVEL, logging.INFO),
        format=LOGGING_FORMAT,
        filemode="a",
    )


def registrar_rutas(app):
    app.register_blueprint(rutas_publicas)
    app.register_blueprint(rutas_admin)
