import mysql.connector
from mysql.connector import Error
import logging

logging.basicConfig(filename='document_processor.log', level=logging.INFO, 
                    format='%(asctime)s - %(levelname)s - %(message)s')

class DBConnector:
    def __init__(self, host='localhost', user='root', password='2312', database='servicio'):
        self.config = {
            'host': host,
            'user': user,
            'password': password,
            'database': database
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