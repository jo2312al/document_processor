import pandas as pd
import random
import os
import logging
import argparse
from datetime import datetime, timedelta
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))
from config import BASE_DIR, DATA_DIR, LOGS_DIR, LOGGING_FORMAT, LOGGING_LEVEL
from src.database.db_connector import DBConnector

# Configurar rutas
NAMES_CSV = os.path.join(DATA_DIR, 'nombres_apellidos.csv')
OUTPUT_CSV = os.path.join(DATA_DIR, 'datos_prueba.csv')

# Crear directorios
os.makedirs(LOGS_DIR, exist_ok=True)
os.makedirs(DATA_DIR, exist_ok=True)

# Configurar logging
logging.basicConfig(
    filename=os.path.join(LOGS_DIR, 'document_processor.log'),
    level=getattr(logging, LOGGING_LEVEL),
    format=LOGGING_FORMAT
)

meses_espanol = [
    'ENERO', 'FEBRERO', 'MARZO', 'ABRIL', 'MAYO', 'JUNIO',
    'JULIO', 'AGOSTO', 'SEPTIEMBRE', 'OCTUBRE', 'NOVIEMBRE', 'DICIEMBRE'
]

def generar_servicio():
    start_date = datetime(1974, 1, 1)
    end_date = datetime(2025, 12, 31)
    inicio = start_date + timedelta(days=random.randint(0, (end_date - start_date).days))
    fin = inicio + timedelta(days=180)
    dia_inicio = inicio.day
    mes_inicio = meses_espanol[inicio.month - 1]
    anio_inicio = inicio.year
    dia_fin = fin.day
    mes_fin = meses_espanol[fin.month - 1]
    anio_fin = fin.year
    servicio = f"{dia_inicio} DE {mes_inicio} DE {anio_inicio} AL {dia_fin} DE {mes_fin} DE {anio_fin}"
    if ',' in servicio:
        servicio = servicio.replace(',', '')  # Evitar comas
    return servicio

import random

def generate_matricula(year, add_c_prefix=False):
    year_suffix = str(year)[-2:]
    number = f"{random.randint(0, 9999):04d}"
    matricula = f"{year_suffix}30{number}"
    # Genera el prefijo 'C' solo en el 1% de los casos
    add_c_prefix = random.random() < 0.01
    return f"C{matricula}" if add_c_prefix else matricula

def load_names_surnames(csv_path=NAMES_CSV):
    if not os.path.exists(csv_path):
        logging.error(f"CSV de nombres y apellidos no encontrado en {csv_path}")
        raise FileNotFoundError(f"Ejecuta generate_names_surnames.py para crear {csv_path}")
    return pd.read_csv(csv_path, encoding='utf-8')

def generate_test_data(num_records):
    logger = logging.getLogger(__name__)
    
    if os.path.exists(OUTPUT_CSV):
        logger.info(f"{OUTPUT_CSV} ya existe. Sobrescribiendo.")
        try:
            os.remove(OUTPUT_CSV)
        except Exception as e:
            logger.error(f"Error al eliminar {OUTPUT_CSV}: {e}")
            raise
    
    names_surnames = load_names_surnames()
    
    try:
        db = DBConnector()
        carreras = db.query("SELECT car_nombre FROM carrera") or [
            ('Ingeniería en Sistemas Computacionales',),
            ('Ingeniería Industrial',),
            ('Licenciatura en Administración',),
            ('Ingeniería en Electrónica',),
            ('Licenciatura en Contaduría',)
        ]
    except Exception as e:
        logger.warning(f"Error al conectar a la base de datos: {e}. Usando datos por defecto.")
        carreras = [
            ('Ingeniería en Sistemas Computacionales',),
            ('Ingeniería Industrial',),
            ('Licenciatura en Administración',),
            ('Ingeniería en Electrónica',),
            ('Licenciatura en Contaduría',)
        ]
    
    years = [random.randint(1974, 2025) for _ in range(num_records)]
    
    data = []
    for i in range(num_records):
        person = names_surnames.iloc[i % len(names_surnames)]
        nombre = person['nombre']
        paterno = person['paterno']
        materno = person['materno']
        
        matricula = generate_matricula(years[i], add_c_prefix=random.random() < 0.5)
        
        carrera = random.choice(carreras)[0]
        servicio = generar_servicio()
        
        # Validar datos
        if all([matricula, nombre, paterno, materno, carrera, servicio]) and ',' not in servicio:
            data.append({
                'matricula': matricula,
                'nombre': nombre,
                'paterno': paterno,
                'materno': materno,
                'carrera': carrera,
                'servicio': servicio
            })
        else:
            logger.warning(f"Datos incompletos o inválidos en registro {i}. Saltando.")
    
    if len(data) < num_records:
        logger.error(f"Solo se generaron {len(data)} registros válidos de {num_records} solicitados.")
        raise ValueError(f"No se generaron suficientes registros válidos.")
    
    df = pd.DataFrame(data)
    with open(OUTPUT_CSV, 'w', encoding='utf-8', newline='\n') as f:
        df.to_csv(f, index=False, lineterminator='\n')
    logger.info(f"Generados {num_records} registros en {OUTPUT_CSV}")
    with open(OUTPUT_CSV, 'r', encoding='utf-8') as f:
        lines = f.readlines()
        logger.info(f"Total de líneas en {OUTPUT_CSV}: {len(lines)}")
        logger.info(f"Primeras 5 líneas: {lines[:5]}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Genera datos de prueba.")
    parser.add_argument("--num_records", type=int, default=2500, help="Número de registros a generar")
    args = parser.parse_args()
    
    try:
        generate_test_data(args.num_records)
    except Exception as e:
        logging.error(f"Error en generate_test_data: {str(e)}")
        raise