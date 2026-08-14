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

    def test_admin_muestra_retroalimentacion_en_acciones(self):
        contenido = leer_archivos_admin()

        self.assertIn('crearToast', contenido)
        self.assertIn('mostrarToast', contenido)
        self.assertIn('iniciarAccion', contenido)
        self.assertIn('button:disabled', contenido)
        self.assertIn('Tipo documental creado.', contenido)
        self.assertIn('Campo agregado al documento.', contenido)
        self.assertIn('Plantilla creada desde OCR.', contenido)
        self.assertIn('Documento procesado y OCR cargado.', contenido)
        self.assertIn('Anotacion guardada.', contenido)
        self.assertIn('Lote enviado a entrenamiento.', contenido)
        self.assertIn('API key generada.', contenido)
        self.assertIn('Vista ${nombreTab(tabId)} abierta.', contenido)

    def test_admin_conecta_botones_principales(self):
        contenido = leer_archivos_admin()

        self.assertIn("document.getElementById('refrescar-lotes').onclick", contenido)
        self.assertIn("document.getElementById('abrir-wizard-tipo').onclick", contenido)
        self.assertIn("document.getElementById('cerrar-wizard-tipo').onclick", contenido)
        self.assertIn("document.getElementById('guardar-anotacion').onclick", contenido)
        self.assertIn("document.querySelectorAll('[data-next-tipo]')", contenido)
        self.assertIn("document.querySelectorAll('[data-prev-tipo]')", contenido)
        self.assertIn("document.querySelectorAll('.tab')", contenido)
        self.assertIn("data-accion=\"aprendizaje\"", contenido)
        self.assertIn('entrenarLote(lote.id_lote, evento.currentTarget)', contenido)

    def test_login_contiene_formulario(self):
        contenido = leer_template('login.html')

        self.assertIn('name="usuario"', contenido)
        self.assertIn('name="password"', contenido)
        self.assertIn('Entrar', contenido)


def leer_archivos_admin():
    return '\n'.join([
        leer_template('admin_panel.html'),
        leer_static('admin.js'),
        leer_static('admin.css'),
    ])


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
