import unittest
import tempfile

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

    def test_evalua_solo_campos_presentes_en_documento(self):
        documento = documento_solicitud()
        documento["campos_validados"]["programa"] = ""

        metricas = entrenador.evaluar_modelo(modelo_con_entidades(), tipo_solicitud(), [documento])

        self.assertEqual(metricas["programa"]["total"], 0)
        self.assertEqual(metricas["dependencia"]["total"], 1)

    def test_crea_entidad_alineada_con_simbolos_de_ocr(self):
        nlp = spacy.blank("es")
        documento = {
            "texto_ocr": "Total pagado: $ 8,25.",
            "campos_validados": {"total": "$ 8,25"},
        }
        ejemplo = entrenador.crear_ejemplo_documento(nlp, tipo_factura(), documento)

        self.assertEqual(ejemplo.reference.ents[0].label_, "TOTAL")
        self.assertIn("$", ejemplo.reference.ents[0].text)

    def test_predice_campo_por_contexto_si_modelo_no_detecta(self):
        predicciones = entrenador.predecir_campos(
            spacy.blank("es"),
            '{"invoice_no": "40378170", "invoice_date": "10/15/2012"}',
            {"invoice_no": "INVOICE_NO", "invoice_date": "INVOICE_DATE"},
        )

        self.assertEqual(predicciones["invoice_no"], "40378170")
        self.assertEqual(predicciones["invoice_date"], "10/15/2012")

    def test_predice_factura_con_alias_y_tabla(self):
        predicciones = entrenador.predecir_campos(spacy.blank("es"), texto_factura(), mapa_factura())

        self.assertEqual(predicciones["date_issue"], "10/15/2012")
        self.assertIn("Patel", predicciones["seller"])
        self.assertIn("Jackson", predicciones["client"])
        self.assertEqual(predicciones["total"], "$ 8,25")

    def test_predice_texto_serializado_sin_comerse_siguiente_campo(self):
        texto = "term: 18_months party: Open_Text_Corporation jurisdiction: California effective_date: 2014-07-24"
        mapa = {"term": "TERM", "party": "PARTY", "jurisdiction": "JURISDICTION", "effective_date": "EFFECTIVE_DATE"}
        predicciones = entrenador.predecir_campos(spacy.blank("es"), texto, mapa)

        self.assertEqual(predicciones["term"], "18_months")
        self.assertEqual(predicciones["party"], "Open_Text_Corporation")
        self.assertEqual(predicciones["jurisdiction"], "California")
        self.assertEqual(predicciones["effective_date"], "2014-07-24")

    def test_compara_importes_con_moneda_y_coma_decimal(self):
        self.assertTrue(entrenador.campo_correcto("total", "$8,25", "$ 8,25"))
        self.assertTrue(entrenador.campo_correcto("income", "29312.00", "$29,312.00"))

    def test_compara_fechas_normalizadas(self):
        self.assertTrue(entrenador.campo_correcto("invoice_date", "10/15/2012", "2012-10-15"))
        self.assertFalse(entrenador.campo_correcto("invoice_date", "10/15/2012", "2012-10-16"))

    def test_compara_texto_largo_con_ruido_de_formato(self):
        esperado = "Patel, Thompson and Montgomery<br>356 Kyle Vista"
        obtenido = "Patel Thompson and Montgomery 356 Kyle Vista"

        self.assertTrue(entrenador.campo_correcto("seller", esperado, obtenido))

    def test_recorta_texto_largo_conservando_valor_validado(self):
        texto = "A" * 7000 + " respuesta esperada " + "B" * 7000
        recortado = entrenador.recortar_texto_entrenamiento(texto, {"answer": "respuesta esperada"})

        self.assertLess(len(recortado), 1000)
        self.assertIn("respuesta esperada", recortado)

    def test_crea_modelo_base_desde_modelo_activo_si_existe(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            modelo = spacy.blank("es")
            modelo.add_pipe("ner")
            modelo.to_disk(temp_dir)

            nlp, modelo_nuevo = entrenador.crear_modelo_base({"modelo_activo": temp_dir})

        self.assertFalse(modelo_nuevo)
        self.assertTrue(nlp.has_pipe("ner"))

    def test_no_activa_modelo_con_campo_obligatorio_insuficiente(self):
        decision = entrenador.decidir_activacion(tipo_solicitud(), metricas_campo_debil())

        self.assertFalse(decision["activar"])
        self.assertIn("nombre_completo", decision["recomendaciones"][0])

    def test_activa_modelo_si_mejora_y_cumple_obligatorios(self):
        decision = entrenador.decidir_activacion(tipo_solicitud(), metricas_modelo_apto())

        self.assertTrue(decision["activar"])
        self.assertIn("dependencia", decision["recomendaciones"][0])

    def test_no_bloquea_activacion_si_campo_no_aparece_en_lote(self):
        decision = entrenador.decidir_activacion(tipo_solicitud(), metricas_sin_programa())

        self.assertTrue(decision["activar"])


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


def tipo_factura():
    return {
        "id_tipo_documento": "factura",
        "modelo_activo": "modelo_inexistente",
        "campos": [
            {"clave": "total", "etiqueta_entidad": "TOTAL", "obligatorio": True},
        ],
    }


def mapa_factura():
    return {
        "date_issue": "DATE_ISSUE",
        "seller": "SELLER",
        "client": "CLIENT",
        "total": "TOTAL",
    }


def texto_factura():
    return """Date of issue: 10/15/2012
| **Seller:** | **Client:** |
| :--- | :--- |
| Patel SA<br>Tax Id: 123 | Jackson LLC<br>Tax Id: 456 |
| **Total** | **$ 7,50** | **$ 0,75** | **$ 8,25** |"""


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


def metricas_campo_debil():
    return {
        "activo": metricas_por_campo(0.2, 0.0, 0.5, 0.5),
        "candidato": metricas_por_campo(1.0, 0.0, 0.7, 0.7),
    }


def metricas_modelo_apto():
    return {
        "activo": metricas_por_campo(0.8, 0.8, 0.7, 0.8),
        "candidato": metricas_por_campo(0.8, 0.8, 0.9, 0.8),
    }


def metricas_sin_programa():
    return {
        "activo": metricas_por_campo(0.7, 0.7, 0.7, 0.0, total_programa=0),
        "candidato": metricas_por_campo(0.8, 0.8, 0.8, 0.0, total_programa=0),
    }


def metricas_por_campo(matricula, nombre, dependencia, programa, total_programa=1):
    return {
        "matricula": {"f1": matricula, "total": 1},
        "nombre_completo": {"f1": nombre, "total": 1},
        "dependencia": {"f1": dependencia, "total": 1},
        "programa": {"f1": programa, "total": total_programa},
    }


if __name__ == "__main__":
    unittest.main()
