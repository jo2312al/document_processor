import unittest

import spacy

from src.services import entrenador_lotes_aprendizaje as entrenador


class TestEntrenadorLotesAprendizaje(unittest.TestCase):
    def test_crea_entidades_con_campos_dinamicos(self):
        nlp = spacy.blank("es")
        documento = documento_solicitud()
        ejemplo = entrenador.crear_ejemplo_documento(nlp, tipo_solicitud(), documento)
        etiquetas = {ent.label_ for ent in ejemplo.reference.ents}

        self.assertIn("DEPENDENCIA", etiquetas)
        self.assertIn("PROGRAMA", etiquetas)

    def test_evalua_modelo_con_campos_dinamicos(self):
        modelo = modelo_con_entidades()
        metricas = entrenador.evaluar_modelo(modelo, tipo_solicitud(), [documento_solicitud()])

        self.assertEqual(metricas["dependencia"]["f1"], 1.0)
        self.assertEqual(metricas["programa"]["f1"], 1.0)


def modelo_con_entidades():
    nlp = spacy.blank("es")
    ruler = nlp.add_pipe("entity_ruler")
    ruler.add_patterns([
        {"label": "MATRICULA", "pattern": "24001"},
        {"label": "NOMBRE_COMPLETO", "pattern": "Ana Lopez"},
        {"label": "DEPENDENCIA", "pattern": "Banco de Alimentos"},
        {"label": "PROGRAMA", "pattern": "Apoyo comunitario"},
    ])
    return nlp


def tipo_solicitud():
    return {
        "id_tipo_documento": "solicitud_servicio_social",
        "modelo_activo": "modelo_inexistente",
        "campos": [
            {"clave": "matricula", "etiqueta_entidad": "MATRICULA", "obligatorio": True},
            {"clave": "nombre_completo", "etiqueta_entidad": "NOMBRE_COMPLETO", "obligatorio": True},
            {"clave": "dependencia", "etiqueta_entidad": "DEPENDENCIA", "obligatorio": True},
            {"clave": "programa", "etiqueta_entidad": "PROGRAMA", "obligatorio": True},
        ],
    }


def documento_solicitud():
    return {
        "texto_ocr": "Solicitud 24001 Ana Lopez Banco de Alimentos Apoyo comunitario",
        "campos_validados": {
            "matricula": "24001",
            "nombre_completo": "Ana Lopez",
            "dependencia": "Banco de Alimentos",
            "programa": "Apoyo comunitario",
        },
    }


if __name__ == "__main__":
    unittest.main()
