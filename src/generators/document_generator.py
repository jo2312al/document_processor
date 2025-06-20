from fpdf import FPDF
import os
import logging

# Configurar logging
logging.basicConfig(filename='document_processor.log', level=logging.INFO, 
                    format='%(asctime)s - %(levelname)s - %(message)s')

class DocumentGenerator:
    def __init__(self, output_dir='generated_docs'):
        self.output_dir = output_dir
        self.logger = logging.getLogger(__name__)
        try:
            os.makedirs(output_dir, exist_ok=True)
            # Verificar permisos de escritura
            test_file = os.path.join(output_dir, 'test_write.txt')
            with open(test_file, 'w') as f:
                f.write('test')
            os.remove(test_file)
            self.logger.info(f"Directorio creado o verificado: {output_dir}")
        except PermissionError as e:
            self.logger.error(f"No se tienen permisos para crear o escribir en {output_dir}: {e}")
            raise PermissionError(f"No se tienen permisos para crear o escribir en {output_dir}. Intenta ejecutar como administrador o cambiar el directorio.")
        except Exception as e:
            self.logger.error(f"Error al crear/verificar directorio {output_dir}: {e}")
            raise

    def generate_pdf(self, data):
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font('Arial', size=12)

        # Simular el formato real del documento
        pdf.cell(200, 10, txt="INSTITUTO TECNOLÓGICO DE VILLAHERMOSA", ln=True, align='C')
        pdf.cell(200, 10, txt="DEPARTAMENTO DE GESTIÓN TECNOLÓGICA Y VINCULACIÓN", ln=True, align='C')
        pdf.ln(10)

        pdf.cell(200, 10, txt=f"No. de oficio: SUBPLAN/GTV-SSLQ/0392/2025", ln=True)
        pdf.ln(5)

        pdf.cell(200, 10, txt="Asunto: CONSTANCIA DE LIBERACIÓN DE SERVICIO SOCIAL CON CALIFICACIÓN.", ln=True)
        pdf.ln(10)

        pdf.cell(200, 10, txt="A QUIEN CORRESPONDA:", ln=True)
        pdf.ln(5)

        pdf.multi_cell(0, 10, txt=f"Por medio de la presente se HACE CONSTAR que: Según documentos que obran en los archivos de esta institución a la C. {data['alu_nombre']} {data['alu_paterno']} {data['alu_materno']}, con número de control {data['alu_matricula']}, de la carrera de {data['alu_carrera']}, realizó su SERVICIO SOCIAL en el INSTITUTO TECNOLÓGICO DE VILLAHERMOSA, durante el periodo comprendido del {data['alu_servicio']}, obteniendo un nivel de desempeño Excelente con escala de 4.00.")
        pdf.ln(10)

        pdf.cell(200, 10, txt="Se extiende la presente para los fines legales que interesen, a los 10 días del mes de marzo del año 2025.", ln=True)
        pdf.ln(20)

        pdf.cell(200, 10, txt="ATENTAMENTE", ln=True, align='C')
        pdf.cell(200, 10, txt="Excelencia en Educación Tecnológica", ln=True, align='C')
        pdf.ln(20)

        pdf.cell(200, 10, txt="JOSÉ MANUEL DEHESA MARTÍNEZ", ln=True)
        pdf.cell(200, 10, txt="DIRECTOR DEL INSTITUTO TECNOLÓGICO DE VILLAHERMOSA", ln=True)

        output_path = os.path.join(self.output_dir, f"test_document_{data['alu_matricula']}.pdf")
        try:
            pdf.output(output_path)
            self.logger.info(f"PDF generado exitosamente: {output_path}")
            return output_path
        except PermissionError as e:
            self.logger.error(f"Error de permisos al escribir {output_path}: {e}")
            raise PermissionError(f"No se tienen permisos para escribir el archivo {output_path}. Intenta cerrar aplicaciones que lo estén usando o ejecutar como administrador.")
        except Exception as e:
            self.logger.error(f"Error al generar PDF {output_path}: {e}")
            raise

    def generate_test_data(self):
        return {
            'alu_matricula': 'C21300759',
            'alu_nombre': 'SANDRA RUBÍ',
            'alu_paterno': 'ALVAREZ',
            'alu_materno': 'ALVAREZ',
            'alu_carrera': 'INGENIERÍA AMBIENTAL',
            'alu_servicio': '26 DE AGOSTO DE 2024 AL 26 DE FEBRERO DE 2025',
        }