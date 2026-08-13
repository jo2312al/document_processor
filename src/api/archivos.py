import os

from werkzeug.utils import secure_filename


def validar_pdf_subido(archivo):
    if archivo is None:
        return "No se proporciono archivo PDF"
    if archivo.filename == "":
        return "No se selecciono archivo PDF"
    if not archivo.filename.lower().endswith(".pdf"):
        return "Solo se aceptan documentos PDF"
    return None


def guardar_pdf_temporal(archivo, carpeta_destino, prefijo="pdf"):
    nombre_archivo = secure_filename(archivo.filename)
    ruta_archivo = os.path.join(carpeta_destino, f"{prefijo}_{nombre_archivo}")
    archivo.save(ruta_archivo)
    return ruta_archivo, nombre_archivo


def eliminar_si_existe(ruta_archivo):
    if ruta_archivo and os.path.exists(ruta_archivo):
        os.remove(ruta_archivo)
