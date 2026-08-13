import os
import unittest


class TestAdminTemplate(unittest.TestCase):
    def test_admin_contiene_flujo_principal(self):
        contenido = leer_archivos_admin()

        self.assertIn('form-tipo', contenido)
        self.assertIn('form-campo', contenido)
        self.assertIn('form-modelo', contenido)
        self.assertIn('form-entrenamiento', contenido)
        self.assertIn('form-plantilla', contenido)
        self.assertIn('guardarAnotacion', contenido)
        self.assertIn('X-Admin-Token', contenido)
        self.assertIn('form-api-key', contenido)
        self.assertIn('Conexion API', contenido)
        self.assertIn('/aprendizaje/documentos-validados', contenido)
        self.assertIn('Lotes de entrenamiento', contenido)
        self.assertIn('abrirWizardTipo', contenido)


def leer_archivos_admin():
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    rutas = [
        os.path.join(base_dir, 'src', 'templates', 'admin_panel.html'),
        os.path.join(base_dir, 'src', 'api', 'static', 'admin.js'),
    ]
    return '\n'.join(leer_archivo(ruta) for ruta in rutas)


def leer_archivo(ruta):
    with open(ruta, 'r', encoding='utf-8') as archivo:
        return archivo.read()


if __name__ == '__main__':
    unittest.main()