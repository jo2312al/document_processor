import argparse
import locale
import logging
import os
import random
import sys
from datetime import datetime, timedelta

import mysql.connector
import pandas as pd
from mysql.connector import Error

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), ".")))

try:
    from config import DATA_DIR
except ImportError:
    DATA_DIR = "./data"
    os.makedirs(DATA_DIR, exist_ok=True)

CARRERAS_RESPALDO = [
    "INGENIERIA EN SISTEMAS COMPUTACIONALES",
    "INGENIERIA INDUSTRIAL",
    "INGENIERIA CIVIL",
    "INGENIERIA EN GESTION EMPRESARIAL",
    "LICENCIATURA EN ADMINISTRACION",
]


class ConexionMySQL:
    def __init__(self, host=None, user=None, password=None, database=None):
        self.configuracion = crear_configuracion_mysql(host, user, password, database)
        self.conexion = None
        self.registrador = logging.getLogger("pipeline.conexion_mysql")

    def conectar(self):
        self.conexion = mysql.connector.connect(**self.configuracion)
        self.registrador.info("Conexion a MySQL establecida.")
        return self.conexion

    def cerrar(self):
        if self.conexion and self.conexion.is_connected():
            self.conexion.close()
            self.registrador.info("Conexion a MySQL cerrada.")

    def obtener_carreras(self):
        if not self.conexion or not self.conexion.is_connected():
            return []
        return consultar_carreras(self.conexion)

    def connect(self):
        return self.conectar()

    def close(self):
        self.cerrar()

    def get_carreras(self):
        return self.obtener_carreras()


DBConnector = ConexionMySQL


def generar_datos_prueba(numero_registros, conector_bd=None):
    registrador = logging.getLogger("pipeline.generar_datos_prueba")
    preparar_locale(registrador)
    nombres = cargar_nombres_apellidos()
    carreras = obtener_carreras_disponibles(conector_bd, registrador)
    registros = construir_registros(numero_registros, nombres, carreras)
    guardar_registros_csv(registros)


def generate_test_data(num_records, db_connector=None):
    generar_datos_prueba(num_records, db_connector)


def crear_configuracion_mysql(host, user, password, database):
    return {
        "host": host or os.getenv("MYSQL_HOST", "localhost"),
        "user": user or os.getenv("MYSQL_USER", "root"),
        "password": password if password is not None else os.getenv("MYSQL_PASSWORD", "2312"),
        "database": database or os.getenv("MYSQL_DATABASE", "servicio"),
    }


def consultar_carreras(conexion):
    cursor = conexion.cursor()
    cursor.execute("SELECT car_nombre FROM carrera;")
    carreras = [fila[0] for fila in cursor.fetchall()]
    cursor.close()
    return carreras


def preparar_locale(registrador):
    try:
        locale.setlocale(locale.LC_TIME, "es_ES.UTF-8")
    except locale.Error:
        registrador.warning("Locale es_ES.UTF-8 no disponible; usando locale por defecto.")


def cargar_nombres_apellidos():
    ruta_csv = os.path.join(DATA_DIR, "nombres_apellidos.csv")
    if not os.path.exists(ruta_csv):
        raise FileNotFoundError(f"No se encontro {ruta_csv}.")
    return pd.read_csv(ruta_csv, encoding="utf-8")


def obtener_carreras_disponibles(conector_bd, registrador):
    conector, debe_cerrar = preparar_conector(conector_bd, registrador)
    try:
        carreras = conector.obtener_carreras() if conector else CARRERAS_RESPALDO
    finally:
        if debe_cerrar and conector:
            conector.cerrar()
    return validar_carreras(carreras)


def preparar_conector(conector_bd, registrador):
    if conector_bd is not None:
        return conector_bd, False
    conector = ConexionMySQL()
    try:
        conector.conectar()
        return conector, True
    except Error:
        registrador.warning("MySQL no disponible; usando carreras de respaldo.")
        return None, False


def validar_carreras(carreras):
    if not carreras:
        raise ValueError("No se pudieron obtener carreras de la base de datos.")
    return carreras


def construir_registros(numero_registros, nombres, carreras):
    anios_ingreso = [random.randint(1974, datetime.now().year - 4) for _ in range(numero_registros)]
    return [crear_registro(indice, nombres, carreras, anios_ingreso) for indice in range(numero_registros)]


def crear_registro(indice, nombres, carreras, anios_ingreso):
    persona = nombres.iloc[indice % len(nombres)]
    fecha_inicio = crear_fecha_servicio(anios_ingreso[indice])
    return {
        "matricula": crear_matricula(anios_ingreso[indice]),
        "nombre_completo": crear_nombre_completo(persona),
        "carrera": random.choice(carreras),
        "servicio": crear_periodo_servicio(fecha_inicio),
    }


def crear_nombre_completo(persona):
    return f"{persona['nombre']} {persona['paterno']} {persona['materno']}".strip()


def crear_matricula(anio_ingreso):
    matricula = f"{str(anio_ingreso)[-2:]}30{random.randint(0, 9999):04d}"
    return f"C{matricula}" if random.random() < 0.01 else matricula


def crear_fecha_servicio(anio_ingreso):
    return datetime(anio_ingreso + random.randint(3, 4), random.randint(1, 12), random.randint(1, 28))


def crear_periodo_servicio(fecha_inicio):
    fecha_fin = fecha_inicio + timedelta(days=180)
    return f"{formatear_fecha(fecha_inicio)} AL {formatear_fecha(fecha_fin)}"


def formatear_fecha(fecha):
    return fecha.strftime("%d de %B de %Y").upper()


def guardar_registros_csv(registros):
    ruta_salida = os.path.join(DATA_DIR, "datos_prueba.csv")
    dataframe = pd.DataFrame(registros)
    dataframe.to_csv(ruta_salida, index=False, encoding="utf-8", lineterminator="\n")
    print(f"-> Archivo datos_prueba.csv generado con {len(dataframe)} registros.")


def obtener_argumentos():
    parser = argparse.ArgumentParser(description="Genera datos de prueba para documentos.")
    parser.add_argument("--num_records", type=int, default=10000)
    return parser.parse_args()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    argumentos = obtener_argumentos()
    generar_datos_prueba(argumentos.num_records)
