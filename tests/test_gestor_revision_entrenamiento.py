import tempfile
import unittest
from unittest.mock import patch
import json

from src.services import gestor_revision_entrenamiento as gestor


class TestGestorRevisionEntrenamiento(unittest.TestCase):
    def test_resume_registro_con_id_y_faltantes(self):
        resumen = gestor.resumir_registro(registro_revision())

        self.assertEqual(resumen["pagina"], 3)
        self.assertIn("periodo", resumen["campos_faltantes"])
        self.assertTrue(resumen["apto_entrenamiento"])

    def test_validar_correccion_requiere_algun_dato(self):
        with self.assertRaises(gestor.RegistroRevisionInvalido):
            gestor.validar_correccion({"numero_control": "", "periodo": ""})

    def test_guardar_correccion_registra_documento_validado(self):
        with tempfile.TemporaryDirectory() as directorio:
            ruta = f"{directorio}/reporte.json"
            self._preparar_reporte(ruta)
            with patch.object(gestor, "REPORTE_REVISION", ruta):
                resultado = self._guardar_correccion()

        self.assertEqual(resultado["estado"], "validado")
        self.assertTrue(resultado["registro"]["apto_entrenamiento"])

    def _preparar_reporte(self, ruta):
        with open(ruta, "w", encoding="utf-8") as archivo:
            json.dump({"registros": [registro_revision()]}, archivo)

    def _guardar_correccion(self):
        with patch.object(gestor, "construir_id_revision", return_value="abc123"):
            with patch.object(gestor, "cargar_pagina_pdf", return_value=pagina_pdf()):
                with patch.object(gestor, "registrar_pagina_corregida", return_value=documento_validado()):
                    return gestor.guardar_correccion_revision("abc123", campos_completos())


def registro_revision():
    return {
        "archivo_origen": "cartas.pdf",
        "pagina": 3,
        "campos_validados": {"numero_control": "20300618", "nombre_estudiante": "Ana Ruiz", "carrera": ""},
        "texto_ocr": "Ana Ruiz 20300618",
    }


def campos_completos():
    return {
        "numero_control": "20300618",
        "nombre_estudiante": "Ana Ruiz",
        "carrera": "Ingenieria",
        "periodo": "enero a junio",
    }


def documento_validado():
    return {"id_documento_validado": "doc1", "id_lote": "lote1"}


def pagina_pdf():
    return object()


if __name__ == "__main__":
    unittest.main()
