import os
import unittest


class TestAdminTemplate(unittest.TestCase):
    def test_admin_template_contiene_flujo_principal(self):
        contenido = leer_template_admin()

        self.assertIn('form-tipo', contenido)
        self.assertIn('form-campo', contenido)
        self.assertIn('form-modelo', contenido)
        self.assertIn('form-entrenamiento', contenido)
        self.assertIn('guardar-anotacion', contenido)
        self.assertIn('X-Admin-Token', contenido)
        self.assertIn('form-api-key', contenido)
        self.assertIn('Conexión API', contenido)
        self.assertIn('/aprendizaje/documentos-validados', contenido)
        self.assertIn('Lotes de entrenamiento', contenido)


def leer_template_admin():
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    template_path = os.path.join(base_dir, 'src', 'templates', 'admin_panel.html')
    with open(template_path, 'r', encoding='utf-8') as template_file:
        return template_file.read()


if __name__ == '__main__':
    unittest.main()
