import os
import tempfile
import unittest
from unittest.mock import patch

from src.services import gestor_entrenamiento_documentos as gestor


class TestGestorEntrenamientoDocumentos(unittest.TestCase):
    def test_crear_documento_entrenamiento_y_anotacion(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            contexto = preparar_contexto_temporal(temp_dir)
            with aplicar_contexto_temporal(contexto):
                documento = crear_documento_de_prueba(contexto["pdf_path"])
                anotacion = crear_anotacion_de_prueba(documento)
                documentos = gestor.listar_documentos_entrenamiento("constancia_servicio")

        self.assertEqual(documento["estado"], "ocr_generado")
        self.assertEqual(anotacion["etiqueta_entidad"], "MATRICULA")
        self.assertEqual(len(documentos), 1)
        self.assertEqual(documentos[0]["estado"], "anotado")


def preparar_contexto_temporal(temp_dir):
    pdf_path = os.path.join(temp_dir, "entrada.pdf")
    with open(pdf_path, "wb") as archivo:
        archivo.write(b"%PDF-1.4\n")
    return {"temp_dir": temp_dir, "indice_path": os.path.join(temp_dir, "indice_documentos.json"), "pdf_path": pdf_path}


def aplicar_contexto_temporal(contexto):
    return patch.multiple(
        gestor,
        DOCUMENTOS_ENTRENAMIENTO_DIR=contexto["temp_dir"],
        INDICE_DOCUMENTOS_PATH=contexto["indice_path"],
    )


def crear_documento_de_prueba(pdf_path):
    return gestor.crear_documento_entrenamiento(
        "constancia_servicio",
        pdf_path,
        "entrada.pdf",
        "Matricula 2411367 Nombre Juan",
    )


def crear_anotacion_de_prueba(documento):
    return gestor.agregar_anotacion_entrenamiento(
        documento["id_documento_entrenamiento"],
        datos_anotacion_prueba(),
    )


def datos_anotacion_prueba():
    return {
        "clave_campo": "alu_matricula",
        "etiqueta_entidad": "MATRICULA",
        "texto_anotado": "2411367",
        "posicion_inicio": 10,
        "posicion_fin": 17,
    }


if __name__ == "__main__":
    unittest.main()
