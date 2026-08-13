import unittest

from src.services.gestor_tipos_documento import (
    CatalogoDocumentoInvalido,
    construir_campos_extraidos,
    crear_tipo_documento,
    generar_id_texto,
    listar_tipos_documento,
    obtener_ruta_modelo_activo,
    obtener_tipo_documento,
    usar_mysql,
)


class TestGestorTiposDocumento(unittest.TestCase):
    def test_obtener_tipo_documento_predeterminado(self):
        tipo_documento = obtener_tipo_documento()

        self.assertEqual(tipo_documento["id_tipo_documento"], "constancia_servicio")
        self.assertEqual(tipo_documento["modelo_activo"], "spacy_model")

    def test_listar_tipos_documento_incluye_residencia(self):
        ids = {tipo["id_tipo_documento"] for tipo in listar_tipos_documento()}

        self.assertIn("constancia_servicio", ids)
        self.assertIn("reporte_residencia", ids)

    def test_construir_campos_extraidos_reporta_faltantes(self):
        tipo_documento = obtener_tipo_documento("constancia_servicio")
        campos, faltantes = construir_campos_extraidos(
            tipo_documento,
            {"MATRICULA": "2411367", "NOMBRE": "Juan"},
        )

        self.assertEqual(campos["alu_matricula"]["value"], "2411367")
        self.assertEqual(campos["alu_nombre"]["value"], "Juan")
        self.assertIn("alu_paterno", faltantes)

    def test_obtener_ruta_modelo_activo_usa_modelos(self):
        tipo_documento = obtener_tipo_documento("constancia_servicio")
        ruta_modelo = obtener_ruta_modelo_activo(tipo_documento)

        self.assertTrue(
            ruta_modelo.endswith("models\\spacy_model")
            or ruta_modelo.endswith("models/spacy_model")
        )

    def test_generar_id_texto_normaliza_nombre(self):
        self.assertEqual(
            generar_id_texto("Reporte de Residencia Profesional"),
            "reporte_de_residencia_profesional",
        )

    def test_crear_tipo_documento_requiere_nombre(self):
        with self.assertRaises(CatalogoDocumentoInvalido):
            crear_tipo_documento({"descripcion": "sin nombre"})

    def test_comparar_metricas_modelo_recomienda_mejor_candidato(self):
        from src.services.gestor_tipos_documento import construir_comparacion_modelos

        activo = {"nombre_modelo": "modelo_v1", "metricas": {"f1_entidades": 0.70}}
        candidato = {"nombre_modelo": "modelo_v2", "metricas": {"f1_entidades": 0.82}}
        comparacion = construir_comparacion_modelos(activo, candidato)

        self.assertEqual(comparacion["recomendacion"], "activar")
        self.assertEqual(comparacion["mejora"], 0.12)

    def test_backend_predeterminado_no_es_mysql(self):
        self.assertFalse(usar_mysql())

    def test_repositorio_mysql_importa_sin_conectar(self):
        from src.repositories.catalogo_documental_mysql import CatalogoDocumentalMySQL

        repositorio = CatalogoDocumentalMySQL()
        self.assertIn("host", repositorio.configuracion)


if __name__ == "__main__":
    unittest.main()

