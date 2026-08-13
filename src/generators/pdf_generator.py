import pandas as pd
from fpdf import FPDF
import os
import random
import logging
import json
import sys
import shutil
import argparse
from datetime import datetime
from tqdm import tqdm
from PIL import Image
import tempfile

# --- Configuración de rutas ---
# Asegura que el script pueda encontrar el archivo de configuración
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))
try:
    from config import DATA_DIR, GENERATED_DOCS_DIR, LABELS_DIR, BASE_DIR
except ImportError:
    # Definir rutas por defecto si config.py no está disponible
    BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
    DATA_DIR = os.path.join(BASE_DIR, "data")
    GENERATED_DOCS_DIR = os.path.join(BASE_DIR, "generated_docs")
    LABELS_DIR = os.path.join(BASE_DIR, "labels")


class PDFGenerator:
    def __init__(self, output_dir, labels_dir, img_dir):
        self.output_dir = output_dir
        self.labels_dir = labels_dir
        self.img_dir = img_dir
        self.logger = logging.getLogger("pipeline.pdf_generator")

    def clear_directories(self):
        """Limpia solo archivos generados por el pipeline, no reportes DOCX."""
        self.logger.info("Limpiando PDFs generados y etiquetas del pipeline...")
        os.makedirs(self.output_dir, exist_ok=True)
        os.makedirs(self.labels_dir, exist_ok=True)
        self._remove_files_by_extension(self.output_dir, ".pdf")
        self._remove_files_by_extension(self.labels_dir, ".json")

    def _remove_files_by_extension(self, directory, extension):
        for file_name in os.listdir(directory):
            if file_name.lower().endswith(extension):
                os.remove(os.path.join(directory, file_name))

    def _embed_image(self, pdf, image_path, x, y, w=0, h=0):
        """Inserta una imagen en el PDF, convirtiendo formatos si es necesario."""
        if not os.path.exists(image_path):
            self.logger.warning(f"No se encontró la imagen en: {image_path}")
            return
        
        # Lógica para manejar imágenes .webp (sin cambios)
        temp_image_path = None
        try:
            path_to_use = image_path
            if image_path.lower().endswith('.webp'):
                img = Image.open(image_path).convert("RGB")
                temp_fd, temp_image_path = tempfile.mkstemp(suffix=".png")
                os.close(temp_fd)
                img.save(temp_image_path, 'PNG')
                path_to_use = temp_image_path
            
            pdf.image(path_to_use, x=x, y=y, w=w, h=h)
        except Exception as e:
            self.logger.error(f"FPDF no pudo insertar la imagen {image_path}: {e}")
        finally:
            if temp_image_path and os.path.exists(temp_image_path):
                os.remove(temp_image_path)

    def generate_formato_oficial(self, pdf, row):
        """Genera el contenido del PDF usando la fila de datos."""
        # --- Lógica de logos sin cambios ---
        logo_educacion_path = os.path.join(self.img_dir, 'tecnm.png')
        logo_itvh_path = os.path.join(self.img_dir, 'itvh.png')
        self._embed_image(pdf, logo_educacion_path, x=15, y=12, h=15)
        self._embed_image(pdf, logo_itvh_path, x=165, y=12, h=15)
        
        # --- Lógica de texto sin cambios, excepto la variable del nombre ---
        pdf.set_y(25)
        pdf.set_font('Arial', '', 9)
        pdf.cell(w=0, h=5, txt="Gestión Tecnológica y Vinculación", ln=True, align='C')
        pdf.set_font('Arial', 'B', 9)
        pdf.cell(w=0, h=5, txt=f"No. de oficio: SUBPLAN/GTV-SSL/{random.randint(1000, 9999)}/{datetime.now().year}", ln=True, align='C')
        pdf.ln(10)
        pdf.set_font('Arial', 'B', 10)
        pdf.cell(w=0, h=8, txt="Asunto: CONSTANCIA DE LIBERACIÓN DE SERVICIO SOCIAL", ln=True, align='R')
        pdf.ln(5)
        pdf.set_font('Arial', '', 11)
        pdf.multi_cell(w=0, h=6, txt="A QUIEN CORRESPONDA:", align='L')
        pdf.ln(4)
        
        # --- CAMBIO CLAVE 1: Usar la columna 'nombre_completo' ---
        # En lugar de combinar nombre, paterno y materno, leemos directamente la columna unificada.
        full_name = row.get('nombre_completo', '[NOMBRE COMPLETO AUSENTE]').strip()
        
        texto_principal = (
            f"Por medio de la presente se HACE CONSTAR que el/la C. {full_name}, "
            f"con número de control {row.get('matricula', '[MATRÍCULA]')}, de la carrera de "
            f"{row.get('carrera', '[CARRERA]')}, realizó su SERVICIO SOCIAL en el INSTITUTO TECNOLÓGICO "
            f"DE VILLAHERMOSA, durante el período comprendido del {row.get('servicio', '[PERIODO]')}, "
            f"obteniendo un nivel de desempeño Excelente."
        )
        pdf.multi_cell(w=0, h=7, txt=texto_principal)
        pdf.ln(10)
        pdf.set_font('Arial', 'B', 11)
        pdf.cell(w=0, h=8, txt="ATENTAMENTE", ln=True, align='C')
        pdf.ln(20)
        pdf.cell(w=95, h=5, txt="_____________________________", align='C', ln=False)
        pdf.cell(w=95, h=5, txt="_____________________________", align='C', ln=True)

    def generate_pdf_and_label(self, row, index, pdf_type):
        """Genera un único PDF y su archivo de etiquetas JSON correspondiente."""
        pdf = FPDF(orientation='P', unit='mm', format='A4')
        pdf.add_page()
        pdf.set_text_color(0, 0, 0)
        
        self.generate_formato_oficial(pdf, row)
        
        matricula_limpia = str(row['matricula']).lstrip('C')
        output_filename = f"constancia_{matricula_limpia}_{index}_{pdf_type}.pdf"
        output_path = os.path.join(self.output_dir, output_filename)
        pdf.output(output_path)

        # --- CAMBIO CLAVE 2: Actualizar la estructura de las etiquetas ---
        # Reflejamos la nueva estrategia en el archivo JSON. Solo guardamos 'NOMBRE_COMPLETO'.
        labels = {
            "fields": {
                "alu_matricula": {"value": matricula_limpia},
                "NOMBRE_COMPLETO": {"value": str(row['nombre_completo'])}, # <-- CAMBIO
                "alu_carrera": {"value": str(row['carrera'])},
                "alu_servicio": {"value": str(row['servicio'])}
            },
            "image_dimensions": {"width": int(pdf.w * pdf.k), "height": int(pdf.h * pdf.k)}
        }
        
        label_filename = f"labels_constancia_{matricula_limpia}_{index}_{pdf_type}.json"
        label_path = os.path.join(self.labels_dir, label_filename)
        
        with open(label_path, 'w', encoding='utf-8') as f:
            json.dump(labels, f, ensure_ascii=False, indent=2)

def run_pdf_generation(num_records):
    """Orquesta el proceso de generación de PDFs."""
    logger = logging.getLogger("pipeline.pdf_generator")
    # El script ahora depende del CSV con la columna 'nombre_completo'
    data_file_path = os.path.join(DATA_DIR, 'datos_prueba.csv')
    img_dir_path = os.path.join(BASE_DIR, 'img') # Directorio de imágenes
    
    if not os.path.exists(data_file_path):
        logger.error(f"Archivo de datos no encontrado: {data_file_path}")
        raise FileNotFoundError(f"No se encontró {data_file_path}. Ejecuta 'generate_test_data.py' primero.")

    generator = PDFGenerator(output_dir=GENERATED_DOCS_DIR, labels_dir=LABELS_DIR, img_dir=img_dir_path)
    generator.clear_directories()
    
    data = pd.read_csv(data_file_path, dtype={'matricula': str}).dropna()
    if len(data) < num_records:
        data = pd.concat([data] * (num_records // len(data) + 1), ignore_index=True)
    
    data_to_process = data.sample(n=num_records)
    
    for index, row in tqdm(data_to_process.iterrows(), total=len(data_to_process), desc="Generando PDFs"):
        try:
            generator.generate_pdf_and_label(row, index, "oficial")
        except Exception as e:
            logger.error(f"Fallo al generar PDF para la fila {index}: {e}")

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    
    parser = argparse.ArgumentParser(description="Genera PDFs a partir de datos de prueba.")
    parser.add_argument("--num_records", type=int, default=50, help="Número de PDFs a generar.")
    args = parser.parse_args()
    
    print(f"Generando {args.num_records} PDFs...")
    try:
        run_pdf_generation(args.num_records)
        print("¡Generación de PDFs completada!")
    except Exception as e:
        logging.error(f"Error fatal en la ejecución: {e}", exc_info=True)
        print(f"ERROR: {e}")