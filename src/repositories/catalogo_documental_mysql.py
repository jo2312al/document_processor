from config import MYSQL_DATABASE, MYSQL_HOST, MYSQL_PASSWORD, MYSQL_PORT, MYSQL_USER


class CatalogoDocumentalMySQL:
    def __init__(self):
        self.configuracion = {
            "host": MYSQL_HOST,
            "user": MYSQL_USER,
            "password": MYSQL_PASSWORD,
            "database": MYSQL_DATABASE,
            "port": MYSQL_PORT,
        }

    def conectar(self):
        import mysql.connector

        return mysql.connector.connect(**self.configuracion)

    def listar_tipos_documento(self):
        with self.conectar() as conexion:
            cursor = conexion.cursor(dictionary=True)
            cursor.execute(
                """
                SELECT
                    id_tipo_documento,
                    clave_tipo_documento,
                    nombre,
                    descripcion,
                    estado,
                    paginas_esperadas,
                    origen_documento
                FROM tipos_documento
                ORDER BY nombre
                """
            )
            tipos = cursor.fetchall()

            for tipo in tipos:
                self._hidratar_tipo_documento(cursor, tipo)

            cursor.close()
            return [self._convertir_tipo_documento(tipo) for tipo in tipos]

    def obtener_tipo_documento(self, id_tipo_documento):
        with self.conectar() as conexion:
            cursor = conexion.cursor(dictionary=True)
            cursor.execute(
                """
                SELECT
                    id_tipo_documento,
                    clave_tipo_documento,
                    nombre,
                    descripcion,
                    estado,
                    paginas_esperadas,
                    origen_documento
                FROM tipos_documento
                WHERE clave_tipo_documento = %s
                """,
                (id_tipo_documento,),
            )
            tipo = cursor.fetchone()
            if not tipo:
                cursor.close()
                return None

            self._hidratar_tipo_documento(cursor, tipo)
            cursor.close()
            return self._convertir_tipo_documento(tipo)

    def crear_tipo_documento(self, datos_tipo_documento):
        with self.conectar() as conexion:
            cursor = conexion.cursor(dictionary=True)
            cursor.execute(
                """
                INSERT INTO tipos_documento (
                    clave_tipo_documento,
                    nombre,
                    descripcion,
                    estado,
                    paginas_esperadas,
                    origen_documento
                ) VALUES (%s, %s, %s, %s, %s, %s)
                """,
                (
                    datos_tipo_documento["id_tipo_documento"],
                    datos_tipo_documento["nombre"],
                    datos_tipo_documento.get("descripcion", ""),
                    datos_tipo_documento.get("estado", "borrador"),
                    datos_tipo_documento.get("rasgos_documento", {}).get("paginas_esperadas"),
                    datos_tipo_documento.get("rasgos_documento", {}).get("origen", "escaneado_o_digital"),
                ),
            )
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

            cursor.execute(
                """
                INSERT INTO campos_documento (
                    id_tipo_documento,
                    clave_campo,
                    nombre,
                    etiqueta_entidad,
                    descripcion,
                    obligatorio,
                    tipo_dato,
                    expresion_validacion,
                    orden_visualizacion
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    id_interno,
                    datos_campo["clave"],
                    datos_campo["nombre"],
                    datos_campo["etiqueta_entidad"],
                    datos_campo.get("descripcion", ""),
                    bool(datos_campo.get("obligatorio", False)),
                    datos_campo.get("tipo_dato", "texto"),
                    datos_campo.get("expresion_validacion"),
                    int(datos_campo.get("orden_visualizacion", 0)),
                ),
            )
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

            if datos_modelo.get("activar") is True:
                cursor.execute(
                    """
                    UPDATE versiones_modelo
                    SET estado = 'archivado'
                    WHERE id_tipo_documento = %s AND estado = 'activo'
                    """,
                    (id_interno,),
                )
                estado = "activo"
            else:
                estado = datos_modelo.get("estado", "pruebas")

            cursor.execute(
                """
                INSERT INTO versiones_modelo (
                    id_tipo_documento,
                    nombre_modelo,
                    ruta_modelo,
                    estado,
                    documentos_entrenamiento,
                    precision_entidades,
                    recall_entidades,
                    f1_entidades,
                    observaciones,
                    fecha_entrenamiento
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, NOW())
                """,
                (
                    id_interno,
                    datos_modelo["nombre_modelo"],
                    datos_modelo["ruta_modelo"],
                    estado,
                    int(datos_modelo.get("documentos_entrenamiento", 0)),
                    datos_modelo.get("metricas", {}).get("precision_entidades"),
                    datos_modelo.get("metricas", {}).get("recall_entidades"),
                    datos_modelo.get("metricas", {}).get("f1_entidades"),
                    datos_modelo.get("observaciones", ""),
                ),
            )
            conexion.commit()
            cursor.close()

        version_modelo = dict(datos_modelo)
        version_modelo["estado"] = estado
        return version_modelo

    def _obtener_id_interno_tipo(self, cursor, id_tipo_documento):
        cursor.execute(
            "SELECT id_tipo_documento FROM tipos_documento WHERE clave_tipo_documento = %s",
            (id_tipo_documento,),
        )
        fila = cursor.fetchone()
        return fila["id_tipo_documento"] if fila else None

    def _hidratar_tipo_documento(self, cursor, tipo):
        id_interno = tipo["id_tipo_documento"]
        cursor.execute(
            """
            SELECT
                clave_campo,
                nombre,
                etiqueta_entidad,
                descripcion,
                obligatorio,
                tipo_dato,
                expresion_validacion
            FROM campos_documento
            WHERE id_tipo_documento = %s
            ORDER BY orden_visualizacion, nombre
            """,
            (id_interno,),
        )
        tipo["campos"] = cursor.fetchall()

        cursor.execute(
            """
            SELECT nombre_rasgo, valor_rasgo, peso
            FROM rasgos_documento
            WHERE id_tipo_documento = %s
            ORDER BY peso DESC, nombre_rasgo
            """,
            (id_interno,),
        )
        tipo["rasgos"] = cursor.fetchall()

        cursor.execute(
            """
            SELECT
                nombre_modelo,
                ruta_modelo,
                estado,
                documentos_entrenamiento,
                precision_entidades,
                recall_entidades,
                f1_entidades,
                observaciones,
                fecha_registro
            FROM versiones_modelo
            WHERE id_tipo_documento = %s
            ORDER BY fecha_registro DESC
            """,
            (id_interno,),
        )
        tipo["versiones_modelo"] = cursor.fetchall()

    def _convertir_tipo_documento(self, tipo):
        modelo_activo = "spacy_model"
        for version_modelo in tipo.get("versiones_modelo", []):
            if version_modelo.get("estado") == "activo":
                modelo_activo = version_modelo["nombre_modelo"]
                break

        palabras_clave = [
            rasgo["valor_rasgo"]
            for rasgo in tipo.get("rasgos", [])
            if rasgo.get("nombre_rasgo") == "palabra_clave"
        ]

        return {
            "id_tipo_documento": tipo["clave_tipo_documento"],
            "nombre": tipo["nombre"],
            "descripcion": tipo.get("descripcion") or "",
            "estado": tipo.get("estado", "borrador"),
            "modelo_activo": modelo_activo,
            "campos": [self._convertir_campo(campo) for campo in tipo.get("campos", [])],
            "rasgos_documento": {
                "palabras_clave": palabras_clave,
                "paginas_esperadas": tipo.get("paginas_esperadas"),
                "origen": tipo.get("origen_documento", "escaneado_o_digital"),
            },
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
