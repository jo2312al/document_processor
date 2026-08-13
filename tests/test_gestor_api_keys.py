import os
import tempfile
import unittest
from unittest.mock import patch

from src.services import gestor_api_keys as gestor


class TestGestorApiKeys(unittest.TestCase):
    def test_generar_y_validar_api_key(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = os.path.join(temp_dir, "api_keys.json")
            with patch.object(gestor, "API_KEYS_PATH", path):
                api_key, registro = gestor.generar_api_key({"nombre": "Sistema escolar"})

                self.assertTrue(api_key.startswith("dp_"))
                self.assertEqual(registro["nombre"], "Sistema escolar")
                self.assertNotIn("api_key_hash", registro)
                self.assertTrue(gestor.validar_api_key(api_key))
                self.assertEqual(len(gestor.listar_api_keys()), 1)

    def test_sin_keys_activas_no_bloquea(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = os.path.join(temp_dir, "api_keys.json")
            with patch.object(gestor, "API_KEYS_PATH", path):
                self.assertTrue(gestor.validar_api_key(None))


if __name__ == "__main__":
    unittest.main()
