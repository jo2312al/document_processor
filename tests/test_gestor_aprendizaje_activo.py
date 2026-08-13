import os
import tempfile
import unittest
from unittest.mock import patch

from src.services import gestor_aprendizaje_activo as gestor


class TestGestorAprendizajeActivo(unittest.TestCase):
    def test_registra_revision_por_campos_faltantes(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            ruta = os.path.join(temp_dir, "cola.json")
            resultado = {"confianza_global": 0.42, "campos_faltantes": ["nombre"]}
            with patch.object(gestor, "APRENDIZAJE_ACTIVO_PATH", ruta):
                evento = gestor.registrar_revision_si_aplica("reporte", "doc.pdf", resultado)
                self.assertEqual(evento["motivo"], "campos_obligatorios_faltantes")
                self.assertEqual(len(gestor.listar_eventos_revision("reporte")), 1)

    def test_no_registra_revision_si_confianza_es_suficiente(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            ruta = os.path.join(temp_dir, "cola.json")
            resultado = {"confianza_global": 0.85, "campos_faltantes": []}
            with patch.object(gestor, "APRENDIZAJE_ACTIVO_PATH", ruta):
                self.assertIsNone(gestor.registrar_revision_si_aplica("reporte", "doc.pdf", resultado))


if __name__ == "__main__":
    unittest.main()
