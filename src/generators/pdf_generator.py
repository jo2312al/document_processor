import pandas as pd
from fpdf import FPDF
import os
import random
import logging
import json
import time
import argparse
import shutil
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from config import BASE_DIR, DATA_DIR, LOGS_DIR, GENERATED_DOCS_DIR, LABELS_DIR, LOGGING_FORMAT, LOGGING_LEVEL

# Crear directorios
os.makedirs(LOGS_DIR, exist_ok=True)
os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(GENERATED_DOCS_DIR, exist_ok=True)
os.makedirs(LABELS_DIR, exist_ok=True)

# Configurar logging
logging.basicConfig(
    filename=os.path.join(LOGS_DIR, 'document_processor123.log'),
    level=getattr(logging, LOGGING_LEVEL),
    format=LOGGING_FORMAT
)

class PDFGenerator:
    def __init__(self, output_dir=GENERATED_DOCS_DIR, data_file=os.path.join(DATA_DIR, 'datos_prueba.csv')):
        self.output_dir = output_dir
        self.data_file = data_file
        self.logger = logging.getLogger(__name__)
        # Vaciar las carpetas GENERATED_DOCS_DIR y LABELS_DIR al iniciar
        for dir_to_clear in [self.output_dir, LABELS_DIR]:
            if os.path.exists(dir_to_clear):
                for filename in os.listdir(dir_to_clear):
                    file_path = os.path.join(dir_to_clear, filename)
                    try:
                        if os.path.isfile(file_path):
                            os.unlink(file_path)
                        elif os.path.isdir(file_path):
                            shutil.rmtree(file_path)
                        self.logger.info(f"Eliminado: {file_path}")
                    except Exception as e:
                        self.logger.warning(f"Error al eliminar {file_path}: {e}")
        self.logger.info(f"Directorios configurados: output={output_dir}, data={data_file}")
        print(f"Output directory: {output_dir}")  # Para depuración

    def generate_formato_pdf(self, pdf, row, index):
        """Genera PDF tipo formato con estructura formal optimizada para una sola página."""
        pdf.set_auto_page_break(auto=False)
        pdf.set_margins(left=15, top=15, right=15)
        pdf.add_page()

        pdf.set_font('Arial', 'B', 12)
        pdf.cell(w=0, h=8, txt="INSTITUTO TECNOLÓGICO DE VILLAHERMOSA", ln=True, align='C')
        pdf.set_font('Arial', '', 10)
        pdf.cell(w=0, h=8, txt="Departamento de Gestión Tecnológica y Vinculación", ln=True, align='C')
        pdf.ln(5)

        current_year = 2025
        pdf.cell(w=0, h=8, txt=f"No. de oficio: SUBPLAN/GTV-SSL/{random.randint(1000, 9999)}/{current_year}", ln=True, align='C')
        pdf.ln(5)

        pdf.set_font('Arial', 'B', 10)
        pdf.cell(w=0, h=8, txt="Asunto: CONSTANCIA DE LIBERACIÓN DE SERVICIO SOCIAL CON CALIFICACIÓN", ln=True, align='C')
        pdf.ln(5)

        pdf.set_font('Arial', '', 10)
        pdf.multi_cell(w=0, h=6, txt="A QUIEN CORRESPONDA:", align='L')
        pdf.ln(3)
        pdf.multi_cell(w=0, h=6, txt="Por medio de la presente se HACE CONSTAR que:", align='L')
        pdf.ln(3)
        full_name = f"{row.get('nombre', '')} {row.get('paterno', '')} {row.get('materno', '')}".strip()
        pdf.multi_cell(w=0, h=6, txt=f"Según documentos que obran en los archivos de esta institución, la C. {full_name}, con número de control {row.get('matricula', '[MATRÍCULA]')}, de la carrera de {row.get('carrera', '[CARRERA]')}, realizó su SERVICIO SOCIAL en el INSTITUTO TECNOLÓGICO de VILLAHERMOSA, participando en el programa: APOYO A LA EDUCACIÓN, cubriendo un total de 480 horas, durante el período comprendido del 26 DE AGOSTO DE {current_year-1} AL 26 DE FEBRERO DE {current_year}, obteniendo un nivel de desempeño Excelente con escala de 4.0.")
        pdf.ln(3)
        pdf.multi_cell(w=0, h=6, txt="Este servicio social fue realizado de acuerdo a lo establecido en la Ley Reglamentaria del Artículo 5° Constitucional relativo al ejercicio de las Profesiones y los Reglamentos que rigen al Tecnológico Nacional de México.")
        pdf.ln(3)
        pdf.multi_cell(w=0, h=6, txt=f"Se extiende la presente para los fines legales que interesen, convengan, en la ciudad de Villahermosa, Tabasco, a los {random.randint(1, 28)} días del mes de junio de {current_year}.")

        pdf.ln(10)
        pdf.set_font('Arial', 'B', 10)
        pdf.cell(w=0, h=8, txt="ATENTAMENTE", ln=True, align='C')
        pdf.ln(5)
        pdf.cell(w=0, h=8, txt="Excelencia en Educación Tecnológica®", ln=True, align='C')
        pdf.ln(5)
        pdf.cell(w=80, h=8, txt="_____________________________", ln=False)
        pdf.cell(w=0, h=8, txt="_____________________________", ln=True)
        pdf.set_font('Arial', '', 9)
        pdf.cell(w=80, h=8, txt="CITLALLI IRIS MARTINEZ SOBERANEZ", ln=False)
        pdf.cell(w=0, h=8, txt="JOSE MANUEL DEHESA MARTINEZ", ln=True)
        pdf.set_font('Arial', 'I', 9)
        pdf.cell(w=80, h=8, txt="JEFA DEL DEPARTAMENTO DE GESTIÓN", ln=False)
        pdf.cell(w=0, h=8, txt="DIRECTOR DEL INSTITUTO TECNOLÓGICO DE", ln=True)
        pdf.cell(w=80, h=8, txt="TECNOLÓGICA Y VINCULACIÓN", ln=False)
        pdf.cell(w=0, h=8, txt="VILLAHERMOSA", ln=True)

        pdf.ln(5)
        pdf.set_font('Arial', '', 7)
        pdf.cell(w=0, h=6, txt="C.P. Servicios Escolares. - Expediente del estudiante", ln=True, align='L')
        pdf.cell(w=0, h=6, txt="Archivo", ln=True, align='L')
        pdf.cell(w=0, h=6, txt="JMJM/RLM/CIMS", ln=True, align='L')
        pdf.ln(3)
        pdf.cell(w=0, h=6, txt="Carretera Villahermosa - Frontera Km. 3.5, Ciudad Industrial,", ln=True, align='C')
        pdf.cell(w=0, h=6, txt="C.P. 86010, Villahermosa, Tabasco [Tel. 9933530299 * Ext. 610", ln=True, align='C')
        pdf.cell(w=0, h=6, txt="Email: vin.villahermosa@tecnm.mx / www.villahermosa.tecnm.mx", ln=True, align='C')

        matricula = str(row['matricula']).lstrip('C')
        output_path = os.path.join(self.output_dir, f"constancia_{matricula}_{index}_formato_page_1.pdf")
        pdf.output(output_path)
        self.logger.info(f"PDF generado: {output_path}")

    def generate_lorem_pdf(self, pdf, row, index):
        """Genera PDF tipo lorem."""
        pdf.set_auto_page_break(auto=False)
        pdf.set_margins(left=15, top=15, right=15)
        pdf.add_page()

        pdf.set_font('Arial', 'B', 12)
        pdf.cell(w=0, h=10, txt="INSTITUTO TECNOLÓGICO DE VILLAHERMOSA", ln=True, align='C')
        pdf.multi_cell(w=0, h=6, txt="Lorem ipsum dolor sit amet, consectetur adipiscing elit.")
        pdf.ln(5)

        matricula = str(row['matricula']).lstrip('C')
        output_path = os.path.join(self.output_dir, f"constancia_{matricula}_{index}_lorem_page_1.pdf")
        pdf.output(output_path)
        self.logger.info(f"PDF generado: {output_path}")

    def generate_random_pdf(self, pdf, row, index):
        """Genera PDF tipo random."""
        pdf.set_auto_page_break(auto=False)
        pdf.set_margins(left=15, top=15, right=15)
        pdf.add_page()

        pdf.set_font('Arial', 'B', 12)
        pdf.cell(w=0, h=10, txt="INSTITUTO TECNOLÓGICO DE VILLAHERMOSA", ln=True, align='C')
        pdf.multi_cell(w=0, h=6, txt=" ".join(random.choice(["sol", "luna", "estrella"]) for _ in range(10)))
        pdf.ln(5)

        matricula = str(row['matricula']).lstrip('C')
        output_path = os.path.join(self.output_dir, f"constancia_{matricula}_{index}_random_page_1.pdf")
        pdf.output(output_path)
        self.logger.info(f"PDF generado: {output_path}")

    def generate_pdf(self, row, index, pdf_type):
        self.logger.info(f"Generando PDF {pdf_type} para fila {index}, matricula: {row['matricula']}")
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font('Arial', size=10)
        pdf.set_text_color(0, 0, 0)

        if pdf_type == "formato":
            self.generate_formato_pdf(pdf, row, index)
        elif pdf_type == "lorem":
            self.generate_lorem_pdf(pdf, row, index)
        elif pdf_type == "random":
            self.generate_random_pdf(pdf, row, index)

        labels = {
            "fields": {
                "alu_matricula": {"value": str(row['matricula']).lstrip('C')},
                "alu_nombre": {"value": str(row['nombre'])},
                "alu_paterno": {"value": str(row['paterno'])},
                "alu_materno": {"value": str(row['materno'])},
                "alu_carrera": {"value": str(row['carrera'])},
                "alu_servicio": {"value": str(row['servicio'])}
            },
            "image_dimensions": {"width": 595, "height": 842}
        }
        label_path = os.path.join(LABELS_DIR, f"labels_constancia_{str(row['matricula']).lstrip('C')}_{index}_{pdf_type}.json")
        if os.path.exists(label_path):
            os.remove(label_path)
            self.logger.info(f"Archivo existente {label_path} eliminado")
        with open(label_path, 'w', encoding='utf-8') as f:
            json.dump(labels, f, ensure_ascii=False, indent=2)
        self.logger.info(f"Etiqueta creada: {label_path}")

    def generate_pdfs(self, num_pdfs, pdf_types):
        """Genera la cantidad especificada de PDFs de los tipos dados."""
        self.logger.info(f"Iniciando generación de {sum(num_pdfs.values())} PDFs para tipos {pdf_types}")
        if not any(pdf_type in ["formato", "lorem", "random"] for pdf_type in pdf_types):
            raise ValueError(f"Tipo de PDF inválido: {pdf_types}")

        if not os.path.exists(self.data_file):
            self.logger.error(f"Archivo {self.data_file} no encontrado")
            raise FileNotFoundError(f"Archivo {self.data_file} no encontrado. Genere datos_prueba.csv primero.")

        try:
            data = pd.read_csv(
                self.data_file,
                encoding='utf-8',
                delimiter=',',
                skip_blank_lines=True,
                na_values=['', ' '],
                names=['matricula', 'nombre', 'paterno', 'materno', 'carrera', 'servicio'],
                skiprows=1,
                engine='python',
                dtype={'matricula': str}
            )
            data = data.dropna(how='all')
            data = data.dropna(subset=['matricula', 'nombre', 'paterno', 'materno', 'carrera', 'servicio'])
            self.logger.info(f"Filas válidas tras filtrado: {len(data)}")
            self.logger.info(f"Primeras filas: \n{data.head().to_string()}")
        except Exception as e:
            self.logger.error(f"Error al leer datos_prueba.csv: {e}")
            raise

        total_pdfs = sum(num_pdfs.values())
        if len(data) < total_pdfs:
            self.logger.warning(f"No hay suficientes filas en datos_prueba.csv ({len(data)}) para {total_pdfs} PDFs. Se reciclarán datos.")
            data = pd.concat([data] * ((total_pdfs // len(data)) + 1), ignore_index=True).iloc[:total_pdfs]

        index = 0
        valid_indices = list(range(len(data)))
        random.shuffle(valid_indices)
        pdf_counts = {pdf_type: 0 for pdf_type in num_pdfs.keys()}
        json_counts = {pdf_type: 0 for pdf_type in num_pdfs.keys()}

        for pdf_type, count in num_pdfs.items():
            for _ in range(count):
                if index >= len(valid_indices):
                    break
                row = data.iloc[valid_indices[index]]
                try:
                    self.generate_pdf(row, index, pdf_type)
                    pdf_counts[pdf_type] += 1
                    json_path = os.path.join(LABELS_DIR, f"labels_constancia_{str(row['matricula']).lstrip('C')}_{index}_{pdf_type}.json")
                    if os.path.exists(json_path):
                        json_counts[pdf_type] += 1
                    index += 1
                except Exception as e:
                    self.logger.error(f"Error al procesar fila {index} para {pdf_type}: {e}, fila={row}")
                    continue

        for pdf_type in num_pdfs.keys():
            self.logger.info(f"Generados {pdf_counts[pdf_type]} PDFs y {json_counts[pdf_type]} JSONs tipo {pdf_type}")
            if pdf_counts[pdf_type] < num_pdfs[pdf_type] or pdf_counts[pdf_type] != json_counts[pdf_type]:
                self.logger.warning(f"Discrepancia: {pdf_counts[pdf_type]}/{num_pdfs[pdf_type]} PDFs, {json_counts[pdf_type]}/{num_pdfs[pdf_type]} JSONs para {pdf_type}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Genera PDFs a partir de datos de prueba.")
    parser.add_argument("--num_pdfs", type=int, default=20, help="Número total de PDFs a generar")
    parser.add_argument("--type", type=str, nargs='+', default=["formato"], choices=["formato", "lorem", "random"], help="Tipos de PDF a generar (puede ser una lista)")
    parser.add_argument("--dist", type=float, nargs=3, default=[0.4, 0.3, 0.3], help="Distribución de tipos [formato, lorem, random] como proporciones")
    args = parser.parse_args()
    
    try:
        # Calcular distribución basada en las proporciones
        total_pdfs = args.num_pdfs
        num_formato = int(total_pdfs * args.dist[0])
        num_lorem = int(total_pdfs * args.dist[1])
        num_random = total_pdfs - num_formato - num_lorem  # Ajustar para que sume exactamente
        num_pdfs = {"formato": num_formato, "lorem": num_lorem, "random": num_random}
        num_pdfs = {k: v for k, v in num_pdfs.items() if k in args.type}

        generator = PDFGenerator()
        generator.generate_pdfs(num_pdfs, args.type)
    except Exception as e:
        logging.error(f"Error en generate_pdfs: {str(e)}")
        raise