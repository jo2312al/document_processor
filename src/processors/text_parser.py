import re
from datetime import date
import logging
from src.database.db_connector import DBConnector

# Configurar logging
logging.basicConfig(filename='document_processor.log', level=logging.INFO, 
                    format='%(asctime)s - %(levelname)s - %(message)s')

class TextParser:
    def __init__(self):
        self.db = DBConnector()
        self.connection = self.db.connect()
        self.logger = logging.getLogger(__name__)

    def parse(self, text):
        data = {
            'alu_matricula': None,
            'alu_nombre': None,
            'alu_paterno': None,
            'alu_materno': None,
            'alu_ingreso': None,
            'alu_generacion_id': None,
            'alu_carrera_id': None,
            'alu_servicio_id': None,
            'ser_anio': None,
            'error_message': None
        }

        try:
            # Normalizar texto: eliminar saltos de línea múltiples y espacios extra
            text = re.sub(r'\n+', ' ', text.strip())
            text = re.sub(r'\s+', ' ', text)
            self.logger.info("Texto normalizado: %s", text)

            # Intentar extraer datos con el formato original
            if self.parse_original_format(text, data):
                self.logger.info("Datos extraídos con formato original")
            # Si falla, intentar con el formato de pruebas
            elif self.parse_test_format(text, data):
                self.logger.info("Datos extraídos con formato de pruebas")
            else:
                self.logger.warning("No se pudo extraer datos con ningún formato")

            # Calcular alu_ingreso si se extrajo la matrícula
            if data['alu_matricula']:
                anio_prefix = int(data['alu_matricula'].lstrip('C')[:2])
                data['alu_ingreso'] = str(1900 + anio_prefix) if anio_prefix > 73 else str(2000 + anio_prefix)
                self.logger.info("Año de ingreso calculado: %s", data['alu_ingreso'])

        except Exception as e:
            data['error_message'] = f"Error procesando documento: {str(e)}"
            self.logger.error("Error procesando documento: %s", str(e))

        self.db.close()
        return data

    def parse_original_format(self, text, data):
        # Extraer No de Control
        matricula_match = re.search(r'(?:número de control|No\.?\s*de\s*Control)\s*([C]?\d{8})', text, re.IGNORECASE)
        if matricula_match:
            data['alu_matricula'] = matricula_match.group(1)
            self.logger.info("Matrícula extraída (original): %s", data['alu_matricula'])

        # Extraer y dividir Nombre Completo
        nombre_completo_match = re.search(r'C\.\s*([A-ZÁÉÍÓÚÑ\s]+),', text, re.IGNORECASE)
        if nombre_completo_match:
            nombre_completo = nombre_completo_match.group(1).strip().split()
            if len(nombre_completo) >= 2:
                data['alu_materno'] = nombre_completo[-1] if len(nombre_completo) > 2 else ''
                data['alu_paterno'] = nombre_completo[-2]
                data['alu_nombre'] = ' '.join(nombre_completo[:-2]) or nombre_completo[0]
            else:
                data['alu_nombre'] = ' '.join(nombre_completo)
            self.logger.info("Nombre: %s, Paterno: %s, Materno: %s (original)", 
                            data['alu_nombre'], data['alu_paterno'], data['alu_materno'])

        # Extraer Carrera y buscar ID
        carrera_match = re.search(r'carrera de\s*([A-ZÁÉÍÓÚÑ\s]+),', text, re.IGNORECASE)
        if carrera_match and self.connection:
            carrera_nombre = carrera_match.group(1).strip()
            carrera_nombre = carrera_nombre.replace('INGENIERIA', 'INGENIERÍA')
            data['alu_carrera_id'] = self.db.get_carrera_id(carrera_nombre)
            self.logger.info("Carrera: %s, ID: %s (original)", carrera_nombre, data['alu_carrera_id'])

        # Extraer Servicio Social y determinar periodo
        servicio_match = re.search(r'del\s*(\d{1,2}\s+DE\s+[A-Z]+\s+DE\s+202[0-5])\s*AL', text, re.IGNORECASE)
        if servicio_match:
            fecha_inicio = servicio_match.group(1)
            mes, anio = self.parse_fecha_inicio(fecha_inicio)
            data['ser_anio'] = anio
            data['alu_servicio_id'] = 1 if 1 <= mes <= 7 else 2
            self.logger.info("Servicio Social: Mes %s, Año %s, Periodo ID %s (original)", mes, anio, data['alu_servicio_id'])

        # Retornar True si se extrajo al menos la matrícula
        return data['alu_matricula'] is not None

    def parse_test_format(self, text, data):
        # Extraer matrícula
        matricula_match = re.search(r'con\s*matrícula\s*([C]?\d{8})', text, re.IGNORECASE)
        if matricula_match:
            data['alu_matricula'] = matricula_match.group(1)
            self.logger.info("Matrícula extraída (pruebas): %s", data['alu_matricula'])

        # Extraer y dividir Nombre Completo
        nombre_completo_match = re.search(r'estudiante\s*([A-ZÁÉÍÓÚÑ\s]+?),\s*con\s*matrícula', text, re.IGNORECASE)
        if nombre_completo_match:
            nombre_completo = nombre_completo_match.group(1).strip().split()
            if len(nombre_completo) >= 3:
                data['alu_nombre'] = ' '.join(nombre_completo[:-2])
                data['alu_paterno'] = nombre_completo[-2]
                data['alu_materno'] = nombre_completo[-1]
            elif len(nombre_completo) == 2:
                data['alu_nombre'] = nombre_completo[0]
                data['alu_paterno'] = nombre_completo[1]
                data['alu_materno'] = ''
            else:
                data['alu_nombre'] = nombre_completo[0]
            self.logger.info("Nombre: %s, Paterno: %s, Materno: %s (pruebas)", 
                            data['alu_nombre'], data['alu_paterno'], data['alu_materno'])

        # Extraer Carrera y buscar ID
        carrera_match = re.search(r'de\s*la\s*carrera\s*([A-ZÁÉÍÓÚÑ\s]+),', text, re.IGNORECASE)
        if carrera_match and self.connection:
            carrera_nombre = carrera_match.group(1).strip()
            carrera_nombre = carrera_nombre.replace('INGENIERIA', 'INGENIERÍA')
            data['alu_carrera_id'] = self.db.get_carrera_id(carrera_nombre)
            self.logger.info("Carrera: %s, ID: %s (pruebas)", carrera_nombre, data['alu_carrera_id'])

        # Extraer Servicio Social y determinar periodo
        servicio_match = re.search(r'del\s*(\d{1,2}\s+DE\s+[A-Z]+\s+DE\s+202[0-5])\s*AL', text, re.IGNORECASE)
        if servicio_match:
            fecha_inicio = servicio_match.group(1)
            mes, anio = self.parse_fecha_inicio(fecha_inicio)
            data['ser_anio'] = anio
            data['alu_servicio_id'] = 1 if 1 <= mes <= 7 else 2
            self.logger.info("Servicio Social: Mes %s, Año %s, Periodo ID %s (pruebas)", mes, anio, data['alu_servicio_id'])

        # Retornar True si se extrajo al menos la matrícula
        return data['alu_matricula'] is not None

    def parse_fecha_inicio(self, fecha):
        meses = {
            'ENERO': 1, 'FEBRERO': 2, 'MARZO': 3, 'ABRIL': 4, 'MAYO': 5, 'JUNIO': 6,
            'JULIO': 7, 'AGOSTO': 8, 'SEPTIEMBRE': 9, 'OCTUBRE': 10, 'NOVIEMBRE': 11, 'DICIEMBRE': 12
        }
        match = re.match(r'\d{1,2}\s+DE\s+([A-Z]+)\s+DE\s+(\d{4})', fecha.upper())
        if match:
            mes_str, anio = match.groups()
            mes = meses.get(mes_str, 1)
            return mes, anio
        self.logger.warning("Fecha de inicio no válida: %s", fecha)
        return 1, str(date.today().year)