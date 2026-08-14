import unittest
from unittest.mock import patch

from api import app


class TestLoginAdmin(unittest.TestCase):
    def test_admin_redirige_a_login_sin_sesion(self):
        cliente = app.test_client()
        respuesta = cliente.get('/admin')

        self.assertEqual(respuesta.status_code, 302)
        self.assertIn('/login', respuesta.headers['Location'])

    def test_login_permite_usar_endpoint_admin(self):
        cliente = app.test_client()
        with patch('src.api.autenticacion.ADMIN_USERNAME', 'admin'):
            with patch('src.api.autenticacion.ADMIN_PASSWORD', 'secreto'):
                respuesta_login = cliente.post('/login', data={'usuario': 'admin', 'password': 'secreto'})
                respuesta_admin = cliente.get('/admin/api-keys')

        self.assertEqual(respuesta_login.status_code, 302)
        self.assertEqual(respuesta_admin.status_code, 200)


if __name__ == '__main__':
    unittest.main()