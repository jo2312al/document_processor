import json
import os
import tempfile
import unittest
from unittest.mock import patch

from src.services import gestor_plantillas_documento as gestor


class TestGestorPlantillasDocumento(unittest.TestCase):
    def tearDown(self):
        limpiar_cache_catalogo()

    def test_crear_plantilla_guarda_campos_ubicados(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            catalogo_path = preparar_catalogo(temp_dir)
            with patch.object(gestor, "extraer_palabras_documento", return_value=palabras_ocr()):
                with patch("src.services.gestor_tipos_documento.TIPOS_DOCUMENTO_PATH", catalogo_path):
                    limpiar_cache_catalogo()
                    plantilla = gestor.crear_plantilla_desde_pdf(
                        "constancia_servicio",
                        os.path.join(temp_dir, "base.pdf"),
                        {"campos_muestra": {"alu_matricula": "2411367", "NOMBRE_COMPLETO": "Juan Perez"}},
                    )

        self.assertEqual(plantilla["campos"][0]["ubicacion"]["x"], 120)
        self.assertEqual(plantilla["campos"][1]["ubicacion"]["ancho"], 100)
        self.assertEqual(plantilla["campos"][0]["confianza"], 91)

    def test_leer_campos_muestra_requiere_datos(self):
        with self.assertRaises(gestor.PlantillaDocumentoInvalida):
            gestor.leer_campos_muestra({})


def preparar_catalogo(temp_dir):
    ruta = os.path.join(temp_dir, "tipos_documento.json")
    catalogo = {"tipos_documento": [{"id_tipo_documento": "constancia_servicio", "nombre": "Constancia"}]}
    with open(ruta, "w", encoding="utf-8") as archivo:
        json.dump(catalogo, archivo)
    return ruta


def palabras_ocr():
    return [
        palabra("Matricula", 40, 20, 70, 10, 93),
        palabra("2411367", 120, 20, 60, 10, 91),
        palabra("Alumno", 40, 50, 50, 10, 90),
        palabra("Juan", 100, 50, 35, 10, 88),
        palabra("Perez", 150, 50, 50, 10, 86),
    ]


def palabra(texto, x, y, ancho, alto, confianza):
    return {"texto": texto, "pagina": 1, "x": x, "y": y, "ancho": ancho, "alto": alto, "confianza": confianza}


def limpiar_cache_catalogo():
    from src.services.gestor_tipos_documento import cargar_catalogo_tipos_documento

    cargar_catalogo_tipos_documento.cache_clear()


if __name__ == "__main__":
    unittest.main()

