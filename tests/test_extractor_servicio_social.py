import unittest

from src.services.extractor_servicio_social import (
    clasificar_servicio_social,
    enriquecer_entidades_servicio_social,
    extraer_entidades_servicio_social,
)


class TestExtractorServicioSocial(unittest.TestCase):
    def test_clasifica_carta_terminacion_servicio_social(self):
        clasificacion = clasificar_servicio_social(texto_carta_terminacion())

        self.assertEqual(clasificacion["familia"], "servicio_social")
        self.assertEqual(clasificacion["subtipo"], "carta_terminacion_servicio_social")
        self.assertGreaterEqual(clasificacion["confianza"], 0.6)

    def test_extrae_campos_comunes_con_formato_variable(self):
        entidades = extraer_entidades_servicio_social(texto_carta_terminacion())

        self.assertEqual(entidades["MATRICULA"], "20300618")
        self.assertEqual(entidades["HORAS"], "480")
        self.assertIn("NAYIVE YEZMIN PANTOJA ROSALES", entidades["NOMBRE_COMPLETO"])
        self.assertIn("LICENCIATURA EN ADMINISTRACION", entidades["CARRERA"])
        self.assertIn("APOYO A LA EDUCACION", entidades["PROGRAMA"])

    def test_enriquece_sin_sobrescribir_modelo(self):
        entidades = enriquecer_entidades_servicio_social(
            texto_carta_terminacion(),
            {"MATRICULA": "VALOR_MODELO"},
        )

        self.assertEqual(entidades["MATRICULA"], "VALOR_MODELO")
        self.assertEqual(entidades["PATERNO"], "PANTOJA")
        self.assertEqual(entidades["MATERNO"], "ROSALES")

    def test_extrae_constancia_liberacion_con_ruido_ocr(self):
        entidades = extraer_entidades_servicio_social(texto_constancia_liberacion())

        self.assertEqual(entidades["MATRICULA"], "211160233")
        self.assertEqual(entidades["NOMBRE_COMPLETO"], "EDGAR JHAREDT SANCHEZ RIVERA")
        self.assertEqual(entidades["CARRERA"], "INGENIERIA INDUSTRIAL")
        self.assertIn("INSTITUTO TECNOLOGICO DE VILLAHERMOSA", entidades["DEPENDENCIA"])
        self.assertIn("APOYO A LA EDUCACION", entidades["PROGRAMA"])

    def test_reemplaza_valor_modelo_con_ruido_por_contexto_limpio(self):
        entidades = enriquecer_entidades_servicio_social(
            texto_constancia_liberacion(),
            {"MATRICULA": "211160233,"},
        )

        self.assertEqual(entidades["MATRICULA"], "211160233")


def texto_carta_terminacion():
    return """
    Oficio Num. SGC/009/2026.
    CARTA DE TERMINACION DE SERVICIO SOCIAL
    Por este medio me permito informarle que el C NAYIVE YEZMIN PANTOJA ROSALES.,
    de la carrera de LICENCIATURA EN ADMINISTRACION con numero de control 20300618,
    realizo su Servicio Social en la dependencia: INSTITUTO TECNOLOGICO DE VILLAHERMOSA,
    en el programa denominado: APOYO A LA EDUCACION.
    Durante el periodo comprendido del 25 DE AGOSTO DE 2025 AL 25 DE FEBRERO DE 2026,
    acumulando un total de 480 horas.
    EDUARDO MARTINEZ CRUZ
    RESPONSABLE DE LOS SISTEMAS DE GESTION DE CALIDAD
    """


def texto_constancia_liberacion():
    return """
    Asunto: CONSTANCIA DE LIBERACION DE SERVICIO SOCIAL CON CALIFICACION.
    Segun documentos que obran en los archivos de esta Institucion al C. EDGAR JHAREDT SANCHEZ RIVERA, con numero
    de control 211160233, de la carrera de INGENIER{A INOUSTRIAL, realizo su SERVICIO SOCIAL en INSTITUTO
    TECNOLOGICO DE VILLAHERMOSA, participando en el programa: APOYO A LA EDUCACION, cubriendo un total de 486
    horas, durante el periodo comprendido del 25 DE AGOSTO DE 2025 AL 25 DE FEBRERO DE 2026.
    """


if __name__ == "__main__":
    unittest.main()
