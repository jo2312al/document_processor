import os
import unittest


class TestAdminTemplate(unittest.TestCase):
    def test_admin_template_contiene_formularios_principales(self):
        base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
        template_path = os.path.join(base_dir, 'src', 'templates', 'admin_panel.html')

        self.assertTrue(os.path.exists(template_path))
        with open(template_path, 'r', encoding='utf-8') as template_file:
            contenido = template_file.read()

        self.assertIn('form-tipo', contenido)
        self.assertIn('form-campo', contenido)
        self.assertIn('form-modelo', contenido)
        self.assertIn('form-entrenamiento', contenido)
        self.assertIn('guardar-anotacion', contenido)
        self.assertIn('X-Admin-Token', contenido)
        self.assertIn('form-api-key', contenido)
        self.assertIn('Conexi?n API', contenido)
        self.assertIn('X-API-Key', contenido)


if __name__ == '__main__':
    unittest.main()
