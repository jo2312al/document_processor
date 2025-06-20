import pandas as pd
import random
import os
import logging
import argparse
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))
from config import BASE_DIR, DATA_DIR, LOGS_DIR, LOGGING_FORMAT, LOGGING_LEVEL

# Configurar logging
os.makedirs(LOGS_DIR, exist_ok=True)
logging.basicConfig(
    filename=os.path.join(LOGS_DIR, 'document_processor.log'),
    level=getattr(logging, LOGGING_LEVEL),
    format=LOGGING_FORMAT
)

def generate_names_surnames(num_records):
    logger = logging.getLogger(__name__)
    
    try:
        # Leer CSVs con los nombres de columnas correctos
        hombres_df = pd.read_csv(os.path.join(DATA_DIR, 'hombres.csv'), encoding='utf-8')
        mujeres_df = pd.read_csv(os.path.join(DATA_DIR, 'mujeres.csv'), encoding='utf-8')
        apellidos_df = pd.read_csv(os.path.join(DATA_DIR, 'apellidos.csv'), encoding='utf-8')
        
        # Confirmar columnas
        hombres_col = 'nombre' if 'nombre' in hombres_df.columns else hombres_df.columns[0]
        mujeres_col = 'nombre' if 'nombre' in mujeres_df.columns else mujeres_df.columns[0]
        apellidos_col = 'apellido' if 'apellido' in apellidos_df.columns else apellidos_df.columns[0]
        
        hombres = hombres_df[hombres_col].dropna().tolist()
        mujeres = mujeres_df[mujeres_col].dropna().tolist()
        apellidos = apellidos_df[apellidos_col].dropna().tolist()
        
        if not (hombres and mujeres and apellidos):
            raise ValueError("Uno o más CSVs están vacíos o no contienen datos válidos.")
        
    except FileNotFoundError as e:
        logger.error(f"Archivo no encontrado: {e}")
        raise FileNotFoundError("Asegúrate de que hombres.csv, mujeres.csv y apellidos.csv están en data/")
    except Exception as e:
        logger.error(f"Error al leer CSVs: {e}")
        raise

    data = []
    for _ in range(num_records):
        if random.random() < 0.5:
            nombre = random.choice(hombres)
            genero = 'M'
        else:
            nombre = random.choice(mujeres)
            genero = 'F'
        
        paterno = random.choice(apellidos)
        materno = random.choice(apellidos)
        
        data.append({
            'nombre': nombre,
            'paterno': paterno,
            'materno': materno,
            'genero': genero
        })
    
    df = pd.DataFrame(data)
    os.makedirs(DATA_DIR, exist_ok=True)
    output_path = os.path.join(DATA_DIR, 'nombres_apellidos.csv')
    df.to_csv(output_path, index=False, encoding='utf-8')
    logger.info(f"Generados {num_records} registros en {output_path}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Genera nombres y apellidos.")
    parser.add_argument("--num_records", type=int, default=5000, help="Número de registros a generar")
    args = parser.parse_args()
    
    try:
        generate_names_surnames(args.num_records)
    except Exception as e:
        logging.error(f"Error en generate_names_surnames: {str(e)}")
        raise