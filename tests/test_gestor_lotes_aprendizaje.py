import os
import tempfile
import unittest
from unittest.mock import patch

from src.services import gestor_lotes_aprendizaje as gestor


class TestGestorLotesAprendizaje(unittest.TestCase):
    def test_registrar_documento_validado_crea_lote_listo(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            contexto = preparar_contexto(temp_dir)
            with patch.object(gestor, "APRENDIZAJE_LOTES_PATH", contexto["estado"]), patch.object(gestor, "DOCUMENTOS_VALIDADOS_DIR", temp_dir), patch.object(gestor, "UMBRAL_LOTE_ENTRENAMIENTO", 1):
                documento, lote = gestor.registrar_documento_validado(
                    "constancia_servicio",
                    contexto["pdf"],
                    "constancia.pdf",
                    campos_validos(),
                    "2411367 Juan Perez Ingenieria ENERO A JULIO",
                )

        self.assertEqual(documento["id_tipo_documento"], "constancia_servicio")
        self.assertEqual(lote["estado"], "listo_para_entrenar")
        self.assertEqual(lote["documentos_acumulados"], 1)

    def test_registrar_documento_validado_requiere_campos(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            contexto = preparar_contexto(temp_dir)
            with patch.object(gestor, "APRENDIZAJE_LOTES_PATH", contexto["estado"]), patch.object(gestor, "DOCUMENTOS_VALIDADOS_DIR", temp_dir):
                with self.assertRaises(gestor.DocumentoValidadoInvalido):
                    gestor.registrar_documento_validado("constancia_servicio", contexto["pdf"], "constancia.pdf", {}, "")

    def test_registrar_documento_validado_usa_obligatorios_del_tipo(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            contexto = preparar_contexto(temp_dir)
            with contexto_solicitud(temp_dir, contexto):
                documento, _ = gestor.registrar_documento_validado(
                    "solicitud_servicio_social",
                    contexto["pdf"],
                    "solicitud.pdf",
                    campos_solicitud_validos(),
                    "Solicitud de Ana Lopez para Banco de Alimentos",
                )

        self.assertEqual(documento["campos_validados"]["dependencia"], "Banco de Alimentos")

    def test_registrar_documento_validado_rechaza_obligatorio_dinamico(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            contexto = preparar_contexto(temp_dir)
            with contexto_solicitud(temp_dir, contexto):
                with self.assertRaisesRegex(gestor.DocumentoValidadoInvalido, "dependencia"):
                    gestor.registrar_documento_validado("solicitud_servicio_social", contexto["pdf"], "solicitud.pdf", {"matricula": "24001"}, "")


def contexto_solicitud(temp_dir, contexto):
    return patch.multiple(
        gestor,
        APRENDIZAJE_LOTES_PATH=contexto["estado"],
        DOCUMENTOS_VALIDADOS_DIR=temp_dir,
        obtener_tipo_documento=lambda _: tipo_solicitud_servicio(),
    )


def preparar_contexto(temp_dir):
    ruta_pdf = os.path.join(temp_dir, "constancia.pdf")
    with open(ruta_pdf, "wb") as archivo:
        archivo.write(b"%PDF-1.4\n")
    return {"pdf": ruta_pdf, "estado": os.path.join(temp_dir, "lotes.json")}


def campos_validos():
    return {
        "alu_matricula": "2411367",
        "NOMBRE_COMPLETO": "Juan Perez",
        "alu_carrera": "Ingenieria",
        "alu_servicio": "ENERO A JULIO",
    }


def tipo_solicitud_servicio():
    return {
        "id_tipo_documento": "solicitud_servicio_social",
        "campos": [
            {"clave": "matricula", "etiqueta_entidad": "MATRICULA", "obligatorio": True},
            {"clave": "nombre_completo", "etiqueta_entidad": "NOMBRE_COMPLETO", "obligatorio": True},
            {"clave": "dependencia", "etiqueta_entidad": "DEPENDENCIA", "obligatorio": True},
            {"clave": "programa", "etiqueta_entidad": "PROGRAMA", "obligatorio": False},
        ],
    }


def campos_solicitud_validos():
    return {
        "matricula": "24001",
        "nombre_completo": "Ana Lopez",
        "dependencia": "Banco de Alimentos",
        "programa": "Apoyo comunitario",
    }


if __name__ == "__main__":
    unittest.main()
