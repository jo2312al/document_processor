import pandas as pd
from fpdf import FPDF
import os
import random
import logging
import json
import shutil
import time
import argparse
import sys
from lorem_text import lorem
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

# Asumimos que el módulo config contiene las constantes necesarias
from config import BASE_DIR, DATA_DIR, LOGS_DIR, LOGGING_FORMAT, LOGGING_LEVEL

# Configurar rutas
OUTPUT_DIR = os.path.join(BASE_DIR, 'generated_docs')
LABELS_DIR = os.path.join(BASE_DIR, 'labels')
DATA_FILE = os.path.join(DATA_DIR, 'datos_prueba.csv')

# Crear directorios
os.makedirs(LOGS_DIR, exist_ok=True)
os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(LABELS_DIR, exist_ok=True)

# Configurar logging
logging.basicConfig(
    filename=os.path.join(LOGS_DIR, 'document_processor123.log'),
    level=getattr(logging, LOGGING_LEVEL),
    format=LOGGING_FORMAT
)

# Fuentes y colores
FONTS = ['Arial', 'Times', 'Courier', 'Consolas', 'ComicSansMS']
COLORS = [(0, 0, 0), (0, 0, 255), (255, 0, 0), (0, 128, 0)]
SIZES = [10, 12, 14, 16]

class PDFGenerator:
    def __init__(self, output_dir=OUTPUT_DIR, data_file=DATA_FILE):
        self.output_dir = output_dir
        self.data_file = data_file
        self.logger = logging.getLogger(__name__)
        self.logger.info(f"Directorios configurados: output={output_dir}, data={data_file}")

    def generate_random_text(self, row, type='random'):
        try:
            nombre_completo = f"{row['nombre']} {row['paterno']} {row['materno']}"
            datos = [
                str(row['matricula']),
                str(row['nombre']),
                str(row['paterno']),
                str(row['materno']),
                str(row['carrera']),
                str(row['servicio'])
            ]
        except Exception as e:
            self.logger.error(f"Error al acceder a datos de row: {e}, row={row}, type={type(row)}")
            raise
        if type == 'lorem':
            text = lorem.paragraphs(3)  # Generar 3 párrafos
            words = text.split()
            for dato in datos:
                pos = random.randint(0, len(words)-1)
                words.insert(pos, dato)
            return ' '.join(words)
        else:
            words = ['xyz', 'qwerty', 'abc123', 'lorem', 'ipsum', 'dolor', 'sit', 'amet']
            text = ' '.join(random.choices(words, k=random.randint(50, 100)))  # 50-100 palabras
            words = text.split()
            for dato in datos:
                pos = random.randint(0, len(words)-1)
                words.insert(pos, dato)
            return ' '.join(words)

    def clear_directories(self):
        self.logger.info(f"Vaciando directorios: {self.output_dir}, {LABELS_DIR}")
        for dir_path in [self.output_dir, LABELS_DIR]:
            if os.path.exists(dir_path):
                for filename in os.listdir(dir_path):
                    file_path = os.path.join(dir_path, filename)
                    for _ in range(10):
                        try:
                            if os.path.isfile(file_path):
                                os.unlink(file_path)
                            elif os.path.isdir(file_path):
                                shutil.rmtree(file_path)
                            break
                        except Exception as e:
                            self.logger.warning(f"Intento fallido al eliminar {file_path}: {e}. Reintentando...")
                            time.sleep(1)
                    else:
                        self.logger.error(f"No se pudo eliminar {file_path} tras varios intentos.")

    def generate_pdf(self, row, index, content_type):
        self.logger.info(f"Generando PDF {content_type} para fila {index}, matricula: {row['matricula']}")
        pdf = FPDF()
        pdf.add_page()
        font = random.choice(FONTS) if random.random() < 0.5 else random.choice(['Courier', 'Consolas'])
        size = random.choice(SIZES)
        color = random.choice(COLORS)
        try:
            if font == 'Consolas':
                pdf.add_font('Consolas', '', r'C:\Windows\Fonts\consola.ttf', uni=True)
                pdf.set_font('Consolas', size=size)
            elif font == 'ComicSansMS':
                pdf.add_font('ComicSansMS', '', r'C:\Windows\Fonts\comic.ttf', uni=True)
                pdf.set_font('ComicSansMS', size=size)
            else:
                pdf.set_font(font, size=size)
        except Exception as e:
            self.logger.warning(f"Fuente {font} no disponible, usando Arial: {str(e)}")
            pdf.set_font('Arial', size=size)
        pdf.set_text_color(*color)

        if content_type == 'lorem':
            pdf.multi_cell(w=0, h=5, txt=self.generate_random_text(row, 'lorem'))
        elif content_type == 'random':
            pdf.multi_cell(w=0, h=5, txt=self.generate_random_text(row, 'random'))
        else:  # formato
            pdf.cell(w=200, h=10, txt="INSTITUTO TECNOLÓGICO DE VILLAHERMOSA", ln=True, align='C')
            pdf.cell(w=200, h=10, txt="DEPARTAMENTO DE GESTIÓN TECNOLÓGICA Y VINCULACIÓN", ln=True, align='C')
            pdf.ln(10)
            year = random.randint(1974, 2025)
            pdf.cell(w=200, h=10, txt=f"No. de oficio: SUBPLAN/GTV-SSLQ/{random.randint(1000, 9999)}/{year}", ln=True)
            pdf.ln(5)
            pdf.cell(w=200, h=10, txt="Asunto: CONSTANCIA DE LIBERACIÓN DE SERVICIO SOCIAL.", ln=True, align='C')
            pdf.ln(10)
            pdf.cell(w=200, h=10, txt="A QUIEN CORRESPONDA:", ln=True)
            pdf.ln(5)
            nombre_completo = f"{row['nombre']} {row['paterno']} {row['materno']}"
            pdf.multi_cell(w=0, h=10, txt=f"Se hace constar que el estudiante {nombre_completo}, con matrícula {row['matricula']}, de la carrera {row['carrera']}, realizó su servicio social del {row['servicio']}.")
            pdf.ln(10)
            pdf.cell(w=200, h=10, txt=f"Villahermosa, Tabasco, a 10 de marzo de {year}", ln=True)
            pdf.ln(20)
            pdf.cell(w=200, h=10, txt="ATENTAMENTE", ln=True, align='C')
            pdf.cell(w=200, h=10, txt="JOSÉ MANUEL DEHESA MARTÍNEZ", ln=True, align='C')
            pdf.cell(w=200, h=10, txt="DIRECTOR", ln=True, align='C')

        # Convertir matricula a cadena antes de usar lstrip
        output_path = os.path.join(self.output_dir, f"constancia_{str(row['matricula']).lstrip('C')}_{index}_{content_type}.pdf")
        pdf.output(output_path)
        self.logger.info(f"PDF generado: {output_path}")

        # Generar etiqueta
        labels = {
            "fields": {
                "alu_matricula": {"value": str(row['matricula'])},
                "alu_nombre": {"value": str(row['nombre'])},
                "alu_paterno": {"value": str(row['paterno'])},
                "alu_materno": {"value": str(row['materno'])},
                "alu_carrera": {"value": str(row['carrera'])},
                "alu_servicio": {"value": str(row['servicio'])}
            }
        }
        label_path = os.path.join(LABELS_DIR, f"labels_constancia_{str(row['matricula']).lstrip('C')}_{index}_{content_type}.json")
        with open(label_path, 'w', encoding='utf-8') as f:
            json.dump(labels, f, ensure_ascii=False, indent=2)
        self.logger.info(f"Etiqueta creada: {label_path}")

    def generate_pdfs(self, num_pdfs=18):
        self.logger.info(f"Iniciando generación de {num_pdfs} PDFs")
        self.clear_directories()

        if not os.path.exists(self.data_file):
            self.logger.error(f"Archivo {self.data_file} no encontrado")
            raise FileNotFoundError(f"Archivo {self.data_file} no encontrado. Ejecute generate_test_data.py primero.")

        # Leer CSV manualmente para depurar
        with open(self.data_file, 'r', encoding='utf-8') as f:
            lines = [line.strip() for line in f if line.strip() and not line.strip().startswith(',')]
            self.logger.info(f"Total de líneas válidas en datos_prueba.csv: {len(lines)}")
            self.logger.info(f"Primeras 5 líneas: {lines[:5]}")

        # Leer con pandas, forzar matricula como string
        try:
            data = pd.read_csv(
                self.data_file,
                encoding='utf-8',
                delimiter=',',
                skip_blank_lines=True,
                na_values=['', ' '],
                names=['matricula', 'nombre', 'paterno', 'materno', 'carrera', 'servicio'],
                skiprows=1,
                nrows=num_pdfs,
                engine='python',
                dtype={'matricula': str}  # Forzar que matricula sea string
            )
            data = data.dropna(how='all')
            data = data.dropna(subset=['matricula', 'nombre', 'paterno', 'materno', 'carrera', 'servicio'])
            # Validar filas
            valid_rows = []
            for _, row in data.iterrows():
                try:
                    if all(col in row and pd.notna(row[col]) for col in ['matricula', 'nombre', 'paterno', 'materno', 'carrera', 'servicio']):
                        valid_rows.append(row)
                    else:
                        self.logger.warning(f"Fila inválida detectada: {row.to_dict()}")
                except Exception as e:
                    self.logger.warning(f"Error al validar fila: {e}, fila={row}")
            data = pd.DataFrame(valid_rows)
            self.logger.info(f"Filas válidas tras filtrado: {len(data)}")
            self.logger.info(f"Columnas: {data.columns.tolist()}")
            self.logger.info(f"Primeras filas: \n{data.head().to_string()}")
        except Exception as e:
            self.logger.error(f"Error al leer datos_prueba.csv: {e}")
            raise

        # Verificar columnas
        expected_columns = ['matricula', 'nombre', 'paterno', 'materno', 'carrera', 'servicio']
        if not all(col in data.columns for col in expected_columns):
            self.logger.error(f"Columnas esperadas no encontradas: {data.columns}")
            raise ValueError(f"Columnas esperadas: {expected_columns}, encontradas: {data.columns.tolist()}")

        # Generar PDFs
        lorem_count = min(num_pdfs // 3, len(data))
        formato_count = min(num_pdfs // 3, len(data) - lorem_count)
        random_count = min(num_pdfs - lorem_count - formato_count, len(data) - lorem_count - formato_count)
        index = 0
        valid_indices = list(range(len(data)))
        random.shuffle(valid_indices)

        # Generar PDFs lorem
        for _ in range(lorem_count):
            if not valid_indices:
                break
            i = valid_indices.pop(0)
            row = data.iloc[i]
            try:
                if isinstance(row, pd.Series):
                    self.logger.info(f"Procesando fila {i} para PDF lorem: {row.to_dict()}")
                    self.generate_pdf(row, index, 'lorem')
                    index += 1
                else:
                    self.logger.warning(f"Fila {i} no es un Series, tipo: {type(row)}, valor: {row}. Saltando...")
            except Exception as e:
                self.logger.error(f"Error al procesar fila {i} para PDF lorem: {e}, fila={row}. Saltando...")
                continue

        # Generar PDFs formato
        for _ in range(formato_count):
            if not valid_indices:
                break
            i = valid_indices.pop(0)
            row = data.iloc[i]
            try:
                if isinstance(row, pd.Series):
                    self.logger.info(f"Procesando fila {i} para PDF formato: {row.to_dict()}")
                    self.generate_pdf(row, index, 'formato')
                    index += 1
                else:
                    self.logger.warning(f"Fila {i} no es un Series, tipo: {type(row)}, valor: {row}. Saltando...")
            except Exception as e:
                self.logger.error(f"Error al procesar fila {i} para PDF formato: {e}, fila={row}. Saltando...")
                continue

        # Generar PDFs random
        for _ in range(random_count):
            if not valid_indices:
                break
            i = valid_indices.pop(0)
            row = data.iloc[i]
            try:
                if isinstance(row, pd.Series):
                    self.logger.info(f"Procesando fila {i} para PDF random: {row.to_dict()}")
                    self.generate_pdf(row, index, 'random')
                    index += 1
                else:
                    self.logger.warning(f"Fila {i} no es un Series, tipo: {type(row)}, valor: {row}. Saltando...")
            except Exception as e:
                self.logger.error(f"Error al procesar fila {i} para PDF random: {e}, fila={row}. Saltando...")
                continue

        # Verificar si se completaron suficientes PDFs
        total_pdfs = index
        self.logger.info(f"PDFs generados: {lorem_count} lorem, {formato_count} formato, {random_count} random, total={total_pdfs}")
        if total_pdfs < num_pdfs:
            self.logger.warning(f"No se generaron suficientes PDFs ({total_pdfs}/{num_pdfs}). Puede haber filas inválidas.")
        else:
            self.logger.info(f"Finalizada generación de {total_pdfs} PDFs")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Genera PDFs a partir de datos de prueba.")
    parser.add_argument("--num_pdfs", type=int, default=18, help="Número de PDFs a generar")
    args = parser.parse_args()
    
    try:
        generator = PDFGenerator()
        generator.generate_pdfs(num_pdfs=args.num_pdfs)
    except Exception as e:
        logging.error(f"Error en generate_pdfs: {str(e)}")
        raise