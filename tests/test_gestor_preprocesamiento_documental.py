import unittest
from unittest.mock import patch

from src.services import gestor_preprocesamiento_documental as gestor


class TestGestorPreprocesamientoDocumental(unittest.TestCase):
    def test_docling_usa_tesseract_como_respaldo_si_no_esta_disponible(self):
        esperado = {"texto": "texto", "metodo": "tesseract"}
        with patch.object(gestor, "extraer_texto_docling", side_effect=gestor.PreprocesamientoNoDisponible("sin docling")):
            with patch.object(gestor, "extraer_texto_tesseract", return_value=esperado):
                resultado = gestor.extraer_texto_documento("archivo.pdf", metodo_solicitado="docling")
                self.assertEqual(resultado["metodo"], "tesseract")
                self.assertIn("Se uso Tesseract", resultado["advertencias"][1])

    def test_elegir_metodo_desde_tipo_documental(self):
        tipo = {"preprocesamiento": {"metodo": "docling"}}
        self.assertEqual(gestor.elegir_metodo_preprocesamiento(tipo), "docling")


if __name__ == "__main__":
    unittest.main()
