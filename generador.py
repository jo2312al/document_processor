import pandas as pd
import random
from datetime import datetime, timedelta
import os
import argparse
import logging
import sys

# --- Configuración de Directorios y Logging ---
# Se asume que este script está en un subdirectorio, ajusta si es necesario.
# Si no, puedes simplemente definir BASE_DIR como el directorio actual.
BASE_DIR = os.path.dirname(os.path.abspath(__file__)) 
DATA_DIR = os.path.join(BASE_DIR, 'data')
LOGS_DIR = os.path.join(BASE_DIR, 'logs')

# Crear directorios si no existen
os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(LOGS_DIR, exist_ok=True)

# Configuración del logging
logging.basicConfig(
    filename=os.path.join(LOGS_DIR, 'generador_datos.log'),
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

def generar_fecha_nacimiento(start_year=1950, end_year=2005):
    """
    Genera una fecha de nacimiento aleatoria en formato dd/mm/yyyy.
    """
    start_date = datetime(start_year, 1, 1)
    end_date = datetime(end_year, 12, 31)
    
    time_between_dates = end_date - start_date
    days_between_dates = time_between_dates.days
    random_number_of_days = random.randrange(days_between_dates)
    
    random_date = start_date + timedelta(days=random_number_of_days)
    return random_date.strftime('%d/%m/%Y')

def generar_datos_personales(num_records):
    """
    Genera nombres completos y fechas de nacimiento a partir de archivos CSV.
    """
    logger = logging.getLogger(__name__)
    
    try:
        # --- Carga de datos desde archivos CSV ---
        hombres_df = pd.read_csv(os.path.join(DATA_DIR, 'hombres.csv'), encoding='utf-8')
        mujeres_df = pd.read_csv(os.path.join(DATA_DIR, 'mujeres.csv'), encoding='utf-8')
        apellidos_df = pd.read_csv(os.path.join(DATA_DIR, 'apellidos.csv'), encoding='utf-8')

        # Detectar el nombre de la columna o usar la primera si no coincide
        hombres_col = 'nombre' if 'nombre' in hombres_df.columns else hombres_df.columns[0]
        mujeres_col = 'nombre' if 'nombre' in mujeres_df.columns else mujeres_df.columns[0]
        apellidos_col = 'apellido' if 'apellido' in apellidos_df.columns else apellidos_df.columns[0]
        
        # Convertir las columnas a listas, eliminando valores nulos
        hombres = hombres_df[hombres_col].dropna().tolist()
        mujeres = mujeres_df[mujeres_col].dropna().tolist()
        apellidos = apellidos_df[apellidos_col].dropna().tolist()
        
        if not (hombres and mujeres and apellidos):
            raise ValueError("Uno o más archivos CSV están vacíos o no contienen datos válidos.")
            
    except FileNotFoundError as e:
        error_msg = f"Archivo no encontrado: {e}. Asegúrate de que 'hombres.csv', 'mujeres.csv' y 'apellidos.csv' estén en la carpeta '{DATA_DIR}'."
        logger.error(error_msg)
        print(f"❌ Error: {error_msg}")
        raise
    except Exception as e:
        logger.error(f"Error al leer los archivos CSV: {e}")
        print(f"❌ Error: No se pudieron leer los archivos CSV. Revisa '{os.path.join(LOGS_DIR, 'generador_datos.log')}' para más detalles.")
        raise

    # --- Generación de los datos ---
    data = []
    for _ in range(num_records):
        # Elige un nombre de hombre o mujer al azar
        nombre = random.choice(hombres) if random.random() < 0.5 else random.choice(mujeres)
        
        # Elige dos apellidos al azar
        paterno = random.choice(apellidos)
        materno = random.choice(apellidos)
        
        nombre_completo = f"{nombre} {paterno} {materno}"
        
        data.append({
            'nombre_completo': nombre_completo,
            'fecha_de_nacimiento': generar_fecha_nacimiento()
        })
        
    logger.info(f"Se generaron {len(data)} registros de datos personales.")
    return data

def guardar_en_csv(data, filename="nombres_fechas_nacimiento.csv"):
    """
    Guarda los datos en un archivo CSV usando pandas.
    """
    logger = logging.getLogger(__name__)
    
    if not data:
        logger.warning("No hay datos para guardar en el archivo CSV.")
        return

    df = pd.DataFrame(data)
    output_path = os.path.join(DATA_DIR, filename)
    
    try:
        df.to_csv(output_path, index=False, encoding='utf-8')
        logger.info(f"Datos guardados exitosamente en '{output_path}'")
        print(f"✅ ¡Éxito! Se han generado {len(df)} registros en el archivo '{output_path}'.")
    except Exception as e:
        logger.error(f"No se pudo guardar el archivo CSV en '{output_path}': {e}")
        print(f"❌ Error: No se pudo guardar el archivo CSV. Revisa '{os.path.join(LOGS_DIR, 'generador_datos.log')}' para más detalles.")
        raise

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generador de Nombres Completos y Fechas de Nacimiento desde CSV.")
    parser.add_argument(
        "--num_records",
        type=int,
        default=5000,
        help="Número de registros a generar."
    )
    args = parser.parse_args()
    
    try:
        datos_generados = generar_datos_personales(args.num_records)
        guardar_en_csv(datos_generados)
    except Exception as e:
        logging.critical(f"Ocurrió un error fatal en la ejecución del script: {e}")
        # Los mensajes de error específicos ya se imprimen en las funciones
        sys.exit(1) # Termina el script con un código de error