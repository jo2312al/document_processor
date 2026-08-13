from config import MYSQL_DATABASE, MYSQL_HOST, MYSQL_PASSWORD, MYSQL_PORT, MYSQL_USER


class CatalogoDocumentalMySQL:
    def __init__(self):
        self.configuracion = _crear_configuracion_mysql()

    def conectar(self):
        import mysql.connector

        return mysql.connector.connect(**self.configuracion)

    def listar_tipos_documento(self):
        with self.conectar() as conexion:
            cursor = conexion.cursor(dictionary=True)
            tipos = self._consultar_tipos(cursor)
            for tipo in tipos:
                self._hidratar_tipo_documento(cursor, tipo)
            cursor.close()
        return [self._convertir_tipo_documento(tipo) for tipo in tipos]

    def obtener_tipo_documento(self, id_tipo_documento):
        with self.conectar() as conexion:
            cursor = conexion.cursor(dictionary=True)
            tipo = self._consultar_tipo(cursor, id_tipo_documento)
            if tipo:
                self._hidratar_tipo_documento(cursor, tipo)
            cursor.close()
        return self._convertir_tipo_documento(tipo) if tipo else None

    def crear_tipo_documento(self, datos_tipo_documento):
        with self.conectar() as conexion:
            cursor = conexion.cursor(dictionary=True)
            self._insertar_tipo(cursor, datos_tipo_documento)
            conexion.commit()
            cursor.close()
        return self.obtener_tipo_documento(datos_tipo_documento["id_tipo_documento"])

    def agregar_campo_documento(self, id_tipo_documento, datos_campo):
        with self.conectar() as conexion:
            cursor = conexion.cursor(dictionary=True)
            id_interno = self._obtener_id_interno_tipo(cursor, id_tipo_documento)
            if id_interno is None:
                cursor.close()
                return None
            self._insertar_campo(cursor, id_interno, datos_campo)
            conexion.commit()
            cursor.close()
        return datos_campo

    def registrar_version_modelo(self, id_tipo_documento, datos_modelo):
        with self.conectar() as conexion:
            cursor = conexion.cursor(dictionary=True)
            id_interno = self._obtener_id_interno_tipo(cursor, id_tipo_documento)
            if id_interno is None:
                cursor.close()
                return None
            estado = self._preparar_estado_modelo(cursor, id_interno, datos_modelo)
            self._insertar_version(cursor, id_interno, datos_modelo, estado)
            conexion.commit()
            cursor.close()
        return _version_con_estado(datos_modelo, estado)

    def _consultar_tipos(self, cursor):
        cursor.execute(_consulta_tipos() + " ORDER BY nombre")
        return cursor.fetchall()

    def _consultar_tipo(self, cursor, id_tipo_documento):
        cursor.execute(_consulta_tipos() + " WHERE clave_tipo_documento = %s", (id_tipo_documento,))
        return cursor.fetchone()

    def _insertar_tipo(self, cursor, datos):
        cursor.execute(_sql_insertar_tipo(), _valores_tipo(datos))

    def _insertar_campo(self, cursor, id_interno, datos):
        cursor.execute(_sql_insertar_campo(), _valores_campo(id_interno, datos))

    def _preparar_estado_modelo(self, cursor, id_interno, datos):
        if datos.get("activar") is True:
            self._archivar_modelos_activos(cursor, id_interno)
            return "activo"
        return datos.get("estado", "pruebas")

    def _archivar_modelos_activos(self, cursor, id_interno):
        cursor.execute(
            "UPDATE versiones_modelo SET estado = 'archivado' WHERE id_tipo_documento = %s AND estado = 'activo'",
            (id_interno,),
        )

    def _insertar_version(self, cursor, id_interno, datos, estado):
        cursor.execute(_sql_insertar_version(), _valores_version(id_interno, datos, estado))

    def _obtener_id_interno_tipo(self, cursor, id_tipo_documento):
        cursor.execute("SELECT id_tipo_documento FROM tipos_documento WHERE clave_tipo_documento = %s", (id_tipo_documento,))
        fila = cursor.fetchone()
        return fila["id_tipo_documento"] if fila else None

    def _hidratar_tipo_documento(self, cursor, tipo):
        id_interno = tipo["id_tipo_documento"]
        tipo["campos"] = self._consultar_campos(cursor, id_interno)
        tipo["rasgos"] = self._consultar_rasgos(cursor, id_interno)
        tipo["versiones_modelo"] = self._consultar_versiones(cursor, id_interno)

    def _consultar_campos(self, cursor, id_interno):
        cursor.execute(_sql_consultar_campos(), (id_interno,))
        return cursor.fetchall()

    def _consultar_rasgos(self, cursor, id_interno):
        cursor.execute(_sql_consultar_rasgos(), (id_interno,))
        return cursor.fetchall()

    def _consultar_versiones(self, cursor, id_interno):
        cursor.execute(_sql_consultar_versiones(), (id_interno,))
        return cursor.fetchall()

    def _convertir_tipo_documento(self, tipo):
        return {
            "id_tipo_documento": tipo["clave_tipo_documento"],
            "nombre": tipo["nombre"],
            "descripcion": tipo.get("descripcion") or "",
            "estado": tipo.get("estado", "borrador"),
            "modelo_activo": _obtener_modelo_activo(tipo),
            "campos": [self._convertir_campo(campo) for campo in tipo.get("campos", [])],
            "rasgos_documento": _convertir_rasgos(tipo),
            "versiones_modelo": tipo.get("versiones_modelo", []),
        }

    def _convertir_campo(self, campo):
        return {
            "clave": campo["clave_campo"],
            "nombre": campo["nombre"],
            "etiqueta_entidad": campo["etiqueta_entidad"],
            "descripcion": campo.get("descripcion") or "",
            "obligatorio": bool(campo.get("obligatorio")),
            "tipo_dato": campo.get("tipo_dato", "texto"),
            "expresion_validacion": campo.get("expresion_validacion"),
        }


def _crear_configuracion_mysql():
    return {"host": MYSQL_HOST, "user": MYSQL_USER, "password": MYSQL_PASSWORD, "database": MYSQL_DATABASE, "port": MYSQL_PORT}


def _consulta_tipos():
    return """
        SELECT id_tipo_documento, clave_tipo_documento, nombre, descripcion,
               estado, paginas_esperadas, origen_documento
        FROM tipos_documento
    """


def _sql_insertar_tipo():
    return """
        INSERT INTO tipos_documento (clave_tipo_documento, nombre, descripcion, estado, paginas_esperadas, origen_documento)
        VALUES (%s, %s, %s, %s, %s, %s)
    """


def _valores_tipo(datos):
    rasgos = datos.get("rasgos_documento", {})
    return (datos["id_tipo_documento"], datos["nombre"], datos.get("descripcion", ""), datos.get("estado", "borrador"), rasgos.get("paginas_esperadas"), rasgos.get("origen", "escaneado_o_digital"))


def _sql_insertar_campo():
    return """
        INSERT INTO campos_documento (id_tipo_documento, clave_campo, nombre, etiqueta_entidad, descripcion, obligatorio, tipo_dato, expresion_validacion, orden_visualizacion)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
    """


def _valores_campo(id_interno, datos):
    return (id_interno, datos["clave"], datos["nombre"], datos["etiqueta_entidad"], datos.get("descripcion", ""), bool(datos.get("obligatorio", False)), datos.get("tipo_dato", "texto"), datos.get("expresion_validacion"), int(datos.get("orden_visualizacion", 0)))


def _sql_insertar_version():
    return """
        INSERT INTO versiones_modelo (id_tipo_documento, nombre_modelo, ruta_modelo, estado, documentos_entrenamiento, precision_entidades, recall_entidades, f1_entidades, observaciones, fecha_entrenamiento)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, NOW())
    """


def _valores_version(id_interno, datos, estado):
    metricas = datos.get("metricas", {})
    return (id_interno, datos["nombre_modelo"], datos["ruta_modelo"], estado, int(datos.get("documentos_entrenamiento", 0)), metricas.get("precision_entidades"), metricas.get("recall_entidades"), metricas.get("f1_entidades"), datos.get("observaciones", ""))


def _sql_consultar_campos():
    return """
        SELECT clave_campo, nombre, etiqueta_entidad, descripcion, obligatorio, tipo_dato, expresion_validacion
        FROM campos_documento WHERE id_tipo_documento = %s ORDER BY orden_visualizacion, nombre
    """


def _sql_consultar_rasgos():
    return "SELECT nombre_rasgo, valor_rasgo, peso FROM rasgos_documento WHERE id_tipo_documento = %s ORDER BY peso DESC, nombre_rasgo"


def _sql_consultar_versiones():
    return """
        SELECT nombre_modelo, ruta_modelo, estado, documentos_entrenamiento,
               precision_entidades, recall_entidades, f1_entidades, observaciones, fecha_registro
        FROM versiones_modelo WHERE id_tipo_documento = %s ORDER BY fecha_registro DESC
    """


def _version_con_estado(datos_modelo, estado):
    version_modelo = dict(datos_modelo)
    version_modelo["estado"] = estado
    return version_modelo


def _obtener_modelo_activo(tipo):
    for version_modelo in tipo.get("versiones_modelo", []):
        if version_modelo.get("estado") == "activo":
            return version_modelo["nombre_modelo"]
    return "spacy_model"


def _convertir_rasgos(tipo):
    return {
        "palabras_clave": _obtener_palabras_clave(tipo),
        "paginas_esperadas": tipo.get("paginas_esperadas"),
        "origen": tipo.get("origen_documento", "escaneado_o_digital"),
    }


def _obtener_palabras_clave(tipo):
    return [rasgo["valor_rasgo"] for rasgo in tipo.get("rasgos", []) if rasgo.get("nombre_rasgo") == "palabra_clave"]
