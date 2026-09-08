import unittest

from src.services import preparador_entrenamiento_servicio_social as preparador


class TestPreparadorEntrenamientoServicioSocial(unittest.TestCase):
    def test_mapea_entidades_a_campos_validados(self):
        campos = preparador.mapear_campos({
            "MATRICULA": "20300618",
            "NOMBRE_COMPLETO": "NAYIVE YEZMIN PANTOJA ROSALES",
            "CARRERA": "LICENCIATURA EN ADMINISTRACION",
            "SERVICIO": "25 DE AGOSTO AL 25 DE FEBRERO",
        })

        self.assertEqual(campos["numero_control"], "20300618")
        self.assertEqual(campos["nombre_estudiante"], "NAYIVE YEZMIN PANTOJA ROSALES")
        self.assertEqual(campos["periodo"], "25 DE AGOSTO AL 25 DE FEBRERO")

    def test_detecta_campos_obligatorios_faltantes(self):
        faltantes = preparador.campos_obligatorios_faltantes({"numero_control": "20300618"})

        self.assertIn("nombre_estudiante", faltantes)
        self.assertIn("carrera", faltantes)
        self.assertIn("periodo", faltantes)

    def test_marca_apto_si_tiene_datos_parciales(self):
        registro = preparador.crear_registro("doc.pdf", 1, "texto", {"numero_control": "20300618"})

        self.assertTrue(registro["apto_entrenamiento"])

    def test_construye_resumen_preparacion(self):
        registros = [{"apto_entrenamiento": True}, {"apto_entrenamiento": False}]

        resumen = preparador.construir_resumen(registros)

        self.assertEqual(resumen["paginas_procesadas"], 2)
        self.assertEqual(resumen["aptas_entrenamiento"], 1)
        self.assertEqual(resumen["rechazadas_revision"], 1)


if __name__ == "__main__":
    unittest.main()
