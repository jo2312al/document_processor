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
        self.assertIn('form-api-key', contenido)
        self.assertIn('Conexion API', contenido)
        self.assertIn('/aprendizaje/documentos-validados', contenido)
        self.assertIn('Lotes de entrenamiento', contenido)
        self.assertIn('abrirWizardTipo', contenido)
        self.assertIn('/logout', contenido)
        self.assertNotIn('token-admin', contenido)
        self.assertNotIn('guardar-token', contenido)

    def test_login_contiene_formulario(self):
        contenido = leer_template('login.html')

        self.assertIn('name="usuario"', contenido)
        self.assertIn('name="password"', contenido)
        self.assertIn('Entrar', contenido)


def leer_archivos_admin():
    return '\n'.join([leer_template('admin_panel.html'), leer_static('admin.js')])


def leer_template(nombre):
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    return leer_archivo(os.path.join(base_dir, 'src', 'templates', nombre))


def leer_static(nombre):
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    return leer_archivo(os.path.join(base_dir, 'src', 'api', 'static', nombre))


def leer_archivo(ruta):
    with open(ruta, 'r', encoding='utf-8') as archivo:
        return archivo.read()


if __name__ == '__main__':
    unittest.main()