import pandas as pd
import random
import os
import logging
import argparse
from datetime import datetime, timedelta
import sys
import locale
import mysql.connector
from mysql.connector import Error

CARRERAS_RESPALDO = [
    "INGENIERIA EN SISTEMAS COMPUTACIONALES",
    "INGENIERIA INDUSTRIAL",
    "INGENIERIA CIVIL",
    "INGENIERIA EN GESTION EMPRESARIAL",
    "LICENCIATURA EN ADMINISTRACION",
]

# --- Configuración de rutas y logging ---
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '.')))
try:
    from config import DATA_DIR
except ImportError:
    DATA_DIR = "./data"
    os.makedirs(DATA_DIR, exist_ok=True)

# --- CLASE PARA LA CONEXIÓN A LA BASE DE DATOS ---
class DBConnector:
    """Maneja la conexión a la base de datos MySQL."""
    def __init__(self, host=None, user=None, password=None, database=None):
        host = host or os.getenv("MYSQL_HOST", "localhost")
        user = user or os.getenv("MYSQL_USER", "root")
        password = password if password is not None else os.getenv("MYSQL_PASSWORD", "2312")
        database = database or os.getenv("MYSQL_DATABASE", "servicio")
        self.config = {'host': host, 'user': user, 'password': password, 'database': database}
        self.connection = None
        self.logger = logging.getLogger("pipeline.db_connector")

    def connect(self):
        """Establece la conexión con la base de datos."""
        try:
            self.connection = mysql.connector.connect(**self.config)
            self.logger.info("Conexión a MySQL establecida.")
            return self.connection
        except Error as e:
            self.logger.error(f"Error conectando a MySQL: {e}")
            raise

    def close(self):
        """Cierra la conexión."""
        if self.connection and self.connection.is_connected():
            self.connection.close()
            self.logger.info("Conexión a MySQL cerrada.")

    def get_carreras(self):
        """Obtiene la lista de todas las carreras desde la tabla 'carrera'."""
        if not self.connection or not self.connection.is_connected():
            self.logger.error("No hay conexión a la base de datos.")
            return []
        
        try:
            cursor = self.connection.cursor()
            cursor.execute("SELECT car_nombre FROM carrera;")
            results = cursor.fetchall()
            cursor.close()
            carreras_list = [item[0] for item in results]
            self.logger.info(f"Se obtuvieron {len(carreras_list)} carreras de la BBDD.")
            return carreras_list
        except Error as e:
            self.logger.error(f"Error al obtener carreras: {e}")
            return []

# --- FUNCIÓN PRINCIPAL DE GENERACIÓN DE DATOS ---
def generate_test_data(num_records, db_connector=None):
    """
    Genera el archivo CSV 'datos_prueba.csv' con una columna 'nombre_completo'
    y usando la lista de carreras de la BBDD.
    """
    logger = logging.getLogger("pipeline.generate_test_data")
    owns_connector = db_connector is None
    if db_connector is None:
        db_connector = DBConnector()
        try:
            db_connector.connect()
        except Error:
            logger.warning("MySQL no disponible; usando carreras de respaldo.")
            db_connector = None
    output_csv = os.path.join(DATA_DIR, 'datos_prueba.csv')
    names_surnames_csv = os.path.join(DATA_DIR, 'nombres_apellidos.csv')
    
    if os.path.exists(output_csv):
        logger.info(f"Sobrescribiendo archivo de datos de prueba existente: {output_csv}")
        os.remove(output_csv)
    
    try:
        locale.setlocale(locale.LC_TIME, 'es_ES.UTF-8')
    except locale.Error:
        logger.warning("Locale 'es_ES.UTF-8' no encontrado, usando default.")

    if not os.path.exists(names_surnames_csv):
        logger.error(f"Archivo de nombres no encontrado: {names_surnames_csv}")
        raise FileNotFoundError(f"No se encontró {names_surnames_csv}.")
        
    names_surnames = pd.read_csv(names_surnames_csv, encoding='utf-8')
    try:
        carreras_list = db_connector.get_carreras() if db_connector else CARRERAS_RESPALDO
    finally:
        if owns_connector and db_connector:
            db_connector.close()

    if not carreras_list:
        logger.error("La lista de carreras está vacía. Abortando.")
        raise ValueError("No se pudieron obtener carreras de la base de datos.")

    data = []
    entry_years = [random.randint(1974, datetime.now().year - 4) for _ in range(num_records)]
    
    for i in range(num_records):
        person = names_surnames.iloc[i % len(names_surnames)]
        nombre_completo = f"{person['nombre']} {person['paterno']} {person['materno']}".strip()
        year_suffix = str(entry_years[i])[-2:]
        matricula = f"{year_suffix}30{random.randint(0, 9999):04d}"
        if random.random() < 0.01: matricula = f"C{matricula}"
        
        start_date = datetime(entry_years[i] + random.randint(3, 4), random.randint(1, 12), random.randint(1, 28))
        end_date = start_date + timedelta(days=180)
        servicio = f"{start_date.strftime('%d de %B de %Y').upper()} AL {end_date.strftime('%d de %B de %Y').upper()}"
        
        data.append({
            'matricula': matricula,
            'nombre_completo': nombre_completo,
            'carrera': random.choice(carreras_list),
            'servicio': servicio
        })
    
    df = pd.DataFrame(data)
    df.to_csv(output_csv, index=False, encoding='utf-8', lineterminator='\n')
    logger.info(f"Generados {len(df)} registros en {output_csv}")
    print(f"-> Archivo 'datos_prueba.csv' generado con {len(df)} registros.")

# --- Bloque de Ejecución Independiente ---
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    
    parser = argparse.ArgumentParser(description="Genera datos de prueba para el procesamiento de documentos.")
    parser.add_argument("--num_records", type=int, default=10000, help="Número de registros a generar")
    args = parser.parse_args()
    
    db_connector = DBConnector()

    try:
        print(f"Conectando a la base de datos...")
        db_connector.connect()
        print(f"Generando {args.num_records} registros de prueba...")
        generate_test_data(args.num_records, db_connector)
        print("¡Datos de prueba generados exitosamente!")
    except Exception as e:
        logging.error(f"Error fatal en la ejecución: {e}", exc_info=True)
        print(f"ERROR: {e}")
    finally:
        db_connector.close()
