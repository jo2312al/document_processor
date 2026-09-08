import unittest
from unittest.mock import patch

import spacy

from src.processors.predict import predecir_entidades


class TestPredictServicioSocial(unittest.TestCase):
    @patch("src.processors.predict._extraer_texto_ocr")
    @patch("src.processors.predict.spacy.load")
    def test_redirige_tipo_legacy_a_servicio_social(self, cargar_modelo, extraer_texto):
        cargar_modelo.return_value = spacy.blank("es")
        extraer_texto.return_value = {
            "texto": texto_servicio_social(),
            "metodo": "tesseract",
            "advertencias": [],
        }

        respuesta = predecir_entidades("documento.pdf", "constancia_servicio", "tesseract")

        self.assertEqual(
            respuesta["tipo_documento"]["id_tipo_documento"],
            "carta_terminacion_servicio_social",
        )
        self.assertIn("numero_control", respuesta["fields"])
        self.assertIn("nombre_estudiante", respuesta["fields"])
        self.assertNotIn("alu_nombre", respuesta["fields"])


def texto_servicio_social():
    return """
    CARTA DE TERMINACION DE SERVICIO SOCIAL
    Por este medio me permito informarle que el C NAYIVE YEZMIN PANTOJA ROSALES,
    de la carrera de LICENCIATURA EN ADMINISTRACION con numero de control 20300618,
    realizo su Servicio Social en la dependencia: INSTITUTO TECNOLOGICO DE VILLAHERMOSA,
    en el programa denominado: APOYO A LA EDUCACION.
    Durante el periodo comprendido del 25 DE AGOSTO DE 2025 AL 25 DE FEBRERO DE 2026,
    acumulando un total de 480 horas.
    """


if __name__ == "__main__":
    unittest.main()
