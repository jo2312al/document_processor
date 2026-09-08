import logging
import os

import mysql.connector
from mysql.connector import Error

logging.basicConfig(filename='document_processor.log', level=logging.INFO, 
                    format='%(asctime)s - %(levelname)s - %(message)s')

class DBConnector:
    def __init__(self, host=None, user=None, password=None, database=None):
        self.config = {
            'host': host or os.getenv("MYSQL_HOST", "localhost"),
            'user': user or os.getenv("MYSQL_USER", "root"),
            'password': password if password is not None else os.getenv("MYSQL_PASSWORD", ""),
            'database': database or os.getenv("MYSQL_DATABASE", "servicio")
        }
        self.connection = None
        self.logger = logging.getLogger(__name__)

    def connect(self):
        try:
            self.connection = mysql.connector.connect(**self.config)
            self.logger.info("Conexión a MySQL establecida")
            return self.connection
        except Error as e:
            self.logger.error("Error conectando a MySQL: %s", e)
            return None

    def close(self):
        if self.connection and self.connection.is_connected():
            self.connection.close()
            self.logger.info("Conexión a MySQL cerrada")

    def get_carrera_id(self, carrera_nombre):
        try:
            cursor = self.connection.cursor()
            cursor.execute("SELECT car_id FROM carrera WHERE car_nombre = %s", (carrera_nombre,))
            result = cursor.fetchone()
            cursor.close()
            return result[0] if result else None
        except Error as e:
            self.logger.error("Error buscando carrera: %s", e)
            return None
