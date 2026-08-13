import argparse
import json
import logging
import os
import random
import sys
import tempfile
from datetime import datetime

import pandas as pd
from fpdf import FPDF
from PIL import Image
from tqdm import tqdm

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

try:
    from config import BASE_DIR, DATA_DIR, GENERATED_DOCS_DIR, LABELS_DIR
except ImportError:
    BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    DATA_DIR = os.path.join(BASE_DIR, "data")
    GENERATED_DOCS_DIR = os.path.join(BASE_DIR, "generated_docs")
    LABELS_DIR = os.path.join(BASE_DIR, "labels")


class GeneradorPDF:
    def __init__(self, carpeta_salida, carpeta_etiquetas, carpeta_imagenes):
        self.carpeta_salida = carpeta_salida
        self.carpeta_etiquetas = carpeta_etiquetas
        self.carpeta_imagenes = carpeta_imagenes
        self.registrador = logging.getLogger("pipeline.generador_pdf")

    def limpiar_directorios(self):
        crear_directorio(self.carpeta_salida)
        crear_directorio(self.carpeta_etiquetas)
        eliminar_por_extension(self.carpeta_salida, ".pdf")
        eliminar_por_extension(self.carpeta_etiquetas, ".json")

    def generar_pdf_y_etiqueta(self, fila, indice, tipo_pdf):
        pdf = crear_pdf_base()
        escribir_formato_oficial(pdf, fila, self.carpeta_imagenes, self.registrador)
        ruta_pdf, matricula = guardar_pdf(pdf, fila, indice, tipo_pdf, self.carpeta_salida)
        guardar_etiqueta(fila, matricula, indice, tipo_pdf, pdf, self.carpeta_etiquetas)
        return ruta_pdf

    def clear_directories(self):
        self.limpiar_directorios()

    def generate_pdf_and_label(self, row, index, pdf_type):
        return self.generar_pdf_y_etiqueta(row, index, pdf_type)


PDFGenerator = GeneradorPDF


def ejecutar_generacion_pdfs(numero_registros):
    registrador = logging.getLogger("pipeline.generador_pdf")
    ruta_datos = validar_csv_datos()
    generador = crear_generador_pdf()
    generador.limpiar_directorios()
    datos = preparar_datos_pdf(ruta_datos, numero_registros)
    generar_lote_pdfs(generador, datos, registrador)


def run_pdf_generation(num_records):
    ejecutar_generacion_pdfs(num_records)


def crear_directorio(ruta):
    os.makedirs(ruta, exist_ok=True)


def eliminar_por_extension(carpeta, extension):
    for nombre_archivo in os.listdir(carpeta):
        if nombre_archivo.lower().endswith(extension):
            os.remove(os.path.join(carpeta, nombre_archivo))


def crear_pdf_base():
    pdf = FPDF(orientation="P", unit="mm", format="A4")
    pdf.add_page()
    pdf.set_text_color(0, 0, 0)
    return pdf


def escribir_formato_oficial(pdf, fila, carpeta_imagenes, registrador):
    insertar_logos(pdf, carpeta_imagenes, registrador)
    escribir_encabezado(pdf)
    escribir_cuerpo(pdf, fila)
    escribir_firmas(pdf)


def insertar_logos(pdf, carpeta_imagenes, registrador):
    insertar_imagen(pdf, os.path.join(carpeta_imagenes, "tecnm.png"), 15, 12, registrador, h=15)
    insertar_imagen(pdf, os.path.join(carpeta_imagenes, "itvh.png"), 165, 12, registrador, h=15)


def insertar_imagen(pdf, ruta_imagen, x, y, registrador, w=0, h=0):
    if not os.path.exists(ruta_imagen):
        registrador.warning("No se encontro la imagen: %s", ruta_imagen)
        return
    ruta_temporal = convertir_webp_si_aplica(ruta_imagen)
    try:
        pdf.image(ruta_temporal or ruta_imagen, x=x, y=y, w=w, h=h)
    finally:
        eliminar_temporal(ruta_temporal)


def convertir_webp_si_aplica(ruta_imagen):
    if not ruta_imagen.lower().endswith(".webp"):
        return None
    descriptor, ruta_temporal = tempfile.mkstemp(suffix=".png")
    os.close(descriptor)
    Image.open(ruta_imagen).convert("RGB").save(ruta_temporal, "PNG")
    return ruta_temporal


def eliminar_temporal(ruta_temporal):
    if ruta_temporal and os.path.exists(ruta_temporal):
        os.remove(ruta_temporal)


def escribir_encabezado(pdf):
    pdf.set_y(25)
    pdf.set_font("Arial", "", 9)
    pdf.cell(w=0, h=5, txt="Gestion Tecnologica y Vinculacion", ln=True, align="C")
    pdf.set_font("Arial", "B", 9)
    pdf.cell(w=0, h=5, txt=crear_numero_oficio(), ln=True, align="C")
    pdf.ln(10)
    pdf.set_font("Arial", "B", 10)
    pdf.cell(w=0, h=8, txt="Asunto: CONSTANCIA DE LIBERACION DE SERVICIO SOCIAL", ln=True, align="R")


def crear_numero_oficio():
    return f"No. de oficio: SUBPLAN/GTV-SSL/{random.randint(1000, 9999)}/{datetime.now().year}"


def escribir_cuerpo(pdf, fila):
    pdf.ln(5)
    pdf.set_font("Arial", "", 11)
    pdf.multi_cell(w=0, h=6, txt="A QUIEN CORRESPONDA:", align="L")
    pdf.ln(4)
    pdf.multi_cell(w=0, h=7, txt=crear_texto_constancia(fila))


def crear_texto_constancia(fila):
    return (
        f"Por medio de la presente se HACE CONSTAR que el/la C. {obtener_nombre(fila)}, "
        f"con numero de control {fila.get('matricula', '[MATRICULA]')}, de la carrera de "
        f"{fila.get('carrera', '[CARRERA]')}, realizo su SERVICIO SOCIAL en el INSTITUTO TECNOLOGICO "
        f"DE VILLAHERMOSA, durante el periodo comprendido del {fila.get('servicio', '[PERIODO]')}, "
        "obteniendo un nivel de desempeno Excelente."
    )


def obtener_nombre(fila):
    return fila.get("nombre_completo", "[NOMBRE COMPLETO AUSENTE]").strip()


def escribir_firmas(pdf):
    pdf.ln(10)
    pdf.set_font("Arial", "B", 11)
    pdf.cell(w=0, h=8, txt="ATENTAMENTE", ln=True, align="C")
    pdf.ln(20)
    pdf.cell(w=95, h=5, txt="_____________________________", align="C", ln=False)
    pdf.cell(w=95, h=5, txt="_____________________________", align="C", ln=True)


def guardar_pdf(pdf, fila, indice, tipo_pdf, carpeta_salida):
    matricula = str(fila["matricula"]).lstrip("C")
    nombre_archivo = f"constancia_{matricula}_{indice}_{tipo_pdf}.pdf"
    ruta_pdf = os.path.join(carpeta_salida, nombre_archivo)
    pdf.output(ruta_pdf)
    return ruta_pdf, matricula


def guardar_etiqueta(fila, matricula, indice, tipo_pdf, pdf, carpeta_etiquetas):
    ruta_etiqueta = os.path.join(carpeta_etiquetas, f"labels_constancia_{matricula}_{indice}_{tipo_pdf}.json")
    with open(ruta_etiqueta, "w", encoding="utf-8") as archivo:
        json.dump(crear_etiqueta(fila, matricula, pdf), archivo, ensure_ascii=False, indent=2)


def crear_etiqueta(fila, matricula, pdf):
    return {
        "fields": crear_campos_etiqueta(fila, matricula),
        "image_dimensions": {"width": int(pdf.w * pdf.k), "height": int(pdf.h * pdf.k)},
    }


def crear_campos_etiqueta(fila, matricula):
    return {
        "alu_matricula": {"value": matricula},
        "NOMBRE_COMPLETO": {"value": str(fila["nombre_completo"])},
        "alu_carrera": {"value": str(fila["carrera"])},
        "alu_servicio": {"value": str(fila["servicio"])},
    }


def validar_csv_datos():
    ruta_datos = os.path.join(DATA_DIR, "datos_prueba.csv")
    if not os.path.exists(ruta_datos):
        raise FileNotFoundError("No se encontro datos_prueba.csv. Ejecuta generate_test_data.py primero.")
    return ruta_datos


def crear_generador_pdf():
    return GeneradorPDF(GENERATED_DOCS_DIR, LABELS_DIR, os.path.join(BASE_DIR, "img"))


def preparar_datos_pdf(ruta_datos, numero_registros):
    datos = pd.read_csv(ruta_datos, dtype={"matricula": str}).dropna()
    datos = repetir_datos_si_hacen_falta(datos, numero_registros)
    return datos.sample(n=numero_registros)


def repetir_datos_si_hacen_falta(datos, numero_registros):
    if len(datos) >= numero_registros:
        return datos
    repeticiones = numero_registros // len(datos) + 1
    return pd.concat([datos] * repeticiones, ignore_index=True)


def generar_lote_pdfs(generador, datos, registrador):
    for indice, fila in tqdm(datos.iterrows(), total=len(datos), desc="Generando PDFs"):
        try:
            generador.generar_pdf_y_etiqueta(fila, indice, "oficial")
        except Exception as error:
            registrador.error("Fallo al generar PDF para fila %s: %s", indice, error)


def obtener_argumentos():
    parser = argparse.ArgumentParser(description="Genera PDFs a partir de datos de prueba.")
    parser.add_argument("--num_records", type=int, default=50)
    return parser.parse_args()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    argumentos = obtener_argumentos()
    ejecutar_generacion_pdfs(argumentos.num_records)
