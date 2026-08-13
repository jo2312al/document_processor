import os
import tempfile
import unittest
from unittest.mock import patch

from src.services import gestor_entrenamiento_documentos as gestor


class TestGestorEntrenamientoDocumentos(unittest.TestCase):
    def test_crear_documento_entrenamiento_y_anotacion(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            indice_path = os.path.join(temp_dir, "indice_documentos.json")
            pdf_path = os.path.join(temp_dir, "entrada.pdf")
            with open(pdf_path, "wb") as archivo:
                archivo.write(b"%PDF-1.4\n")

            with patch.object(gestor, "DOCUMENTOS_ENTRENAMIENTO_DIR", temp_dir), patch.object(gestor, "INDICE_DOCUMENTOS_PATH", indice_path):
                documento = gestor.crear_documento_entrenamiento(
                    "constancia_servicio",
                    pdf_path,
                    "entrada.pdf",
                    "Matricula 2411367 Nombre Juan",
                )
                self.assertEqual(documento["estado"], "ocr_generado")

                anotacion = gestor.agregar_anotacion_entrenamiento(
                    documento["id_documento_entrenamiento"],
                    {
                        "clave_campo": "alu_matricula",
                        "etiqueta_entidad": "MATRICULA",
                        "texto_anotado": "2411367",
                        "posicion_inicio": 10,
                        "posicion_fin": 17,
                    },
                )
                self.assertEqual(anotacion["etiqueta_entidad"], "MATRICULA")

                documentos = gestor.listar_documentos_entrenamiento("constancia_servicio")
                self.assertEqual(len(documentos), 1)
                self.assertEqual(documentos[0]["estado"], "anotado")


if __name__ == "__main__":
    unittest.main()
