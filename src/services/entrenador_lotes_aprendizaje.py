import os
import random
from difflib import SequenceMatcher

import spacy
from spacy.training import Example

from config import EPOCAS_ENTRENAMIENTO_LOTE, MODELS_DIR
from src.services.gestor_lotes_aprendizaje import CAMPOS_OBLIGATORIOS
from src.services.gestor_tipos_documento import obtener_ruta_modelo_activo, obtener_tipo_documento

ETIQUETAS_CAMPO = {
    "alu_matricula": "MATRICULA",
    "NOMBRE_COMPLETO": "NOMBRE_COMPLETO",
    "alu_carrera": "CARRERA",
    "alu_servicio": "SERVICIO",
}


def entrenar_y_evaluar_lote(id_lote, documentos):
    tipo_documento = obtener_tipo_documento(documentos[0]["id_tipo_documento"])
    entrenamiento, validacion = dividir_documentos(documentos)
    ruta_modelo = entrenar_modelo_candidato(tipo_documento, id_lote, entrenamiento)
    metricas = evaluar_modelos(tipo_documento, ruta_modelo, validacion)
    decision = decidir_activacion(metricas)
    return {"ruta_modelo": ruta_modelo, "metricas": metricas, "decision": decision}


def dividir_documentos(documentos):
    documentos_ordenados = list(documentos)
    random.Random(42).shuffle(documentos_ordenados)
    tamano_validacion = max(1, int(len(documentos_ordenados) * 0.2))
    return documentos_ordenados[tamano_validacion:], documentos_ordenados[:tamano_validacion]


def entrenar_modelo_candidato(tipo_documento, id_lote, documentos):
    nlp = crear_modelo_base()
    ejemplos = crear_ejemplos_entrenamiento(nlp, documentos)
    entrenar_ejemplos(nlp, ejemplos)
    return guardar_modelo_candidato(nlp, tipo_documento, id_lote)


def crear_modelo_base():
    nlp = spacy.blank("es")
    nlp.add_pipe("ner")
    return nlp


def crear_ejemplos_entrenamiento(nlp, documentos):
    ejemplos = []
    for documento in documentos:
        ejemplo = crear_ejemplo_documento(nlp, documento)
        if ejemplo:
            ejemplos.append(ejemplo)
    return ejemplos


def crear_ejemplo_documento(nlp, documento):
    texto = documento.get("texto_ocr", "")
    entidades = buscar_entidades_validadas(texto, documento.get("campos_validados", {}))
    if not entidades:
        return None
    return Example.from_dict(nlp.make_doc(texto), {"entities": entidades})


def buscar_entidades_validadas(texto, campos):
    entidades = []
    for clave, etiqueta in ETIQUETAS_CAMPO.items():
        entidad = buscar_entidad(texto, campos.get(clave), etiqueta)
        if entidad:
            entidades.append(entidad)
    return entidades


def buscar_entidad(texto, valor, etiqueta):
    valor = str(valor or "").strip()
    inicio = texto.lower().find(valor.lower())
    if inicio < 0:
        return None
    return inicio, inicio + len(valor), etiqueta


def entrenar_ejemplos(nlp, ejemplos):
    validar_ejemplos_entrenamiento(ejemplos)
    ner = nlp.get_pipe("ner")
    for ejemplo in ejemplos:
        agregar_etiquetas(ner, ejemplo)
    optimizer = nlp.initialize(lambda: ejemplos)
    for _ in range(EPOCAS_ENTRENAMIENTO_LOTE):
        random.shuffle(ejemplos)
        nlp.update(ejemplos, sgd=optimizer, drop=0.25)


def validar_ejemplos_entrenamiento(ejemplos):
    if not ejemplos:
        raise ValueError("El lote no genero ejemplos entrenables.")


def agregar_etiquetas(ner, ejemplo):
    for entidad in ejemplo.reference.ents:
        ner.add_label(entidad.label_)


def guardar_modelo_candidato(nlp, tipo_documento, id_lote):
    nombre_modelo = f"{tipo_documento['id_tipo_documento']}_{id_lote[:8]}"
    ruta_modelo = os.path.join(MODELS_DIR, nombre_modelo)
    os.makedirs(MODELS_DIR, exist_ok=True)
    nlp.to_disk(ruta_modelo)
    return ruta_modelo


def evaluar_modelos(tipo_documento, ruta_candidato, documentos):
    modelo_activo = cargar_modelo_seguro(obtener_ruta_modelo_activo(tipo_documento))
    modelo_candidato = cargar_modelo_seguro(ruta_candidato)
    return {"activo": evaluar_modelo(modelo_activo, documentos), "candidato": evaluar_modelo(modelo_candidato, documentos)}


def cargar_modelo_seguro(ruta_modelo):
    if not os.path.exists(ruta_modelo):
        return None
    return spacy.load(ruta_modelo)


def evaluar_modelo(modelo, documentos):
    resultados = {campo: {"correctos": 0, "total": 0, "f1": 0.0} for campo in CAMPOS_OBLIGATORIOS}
    for documento in documentos:
        evaluar_documento(modelo, documento, resultados)
    return calcular_f1_campos(resultados)


def evaluar_documento(modelo, documento, resultados):
    predicciones = predecir_campos(modelo, documento.get("texto_ocr", ""))
    for campo in CAMPOS_OBLIGATORIOS:
        esperado = documento.get("campos_validados", {}).get(campo, "")
        resultados[campo]["total"] += 1
        if campo_correcto(campo, esperado, predicciones.get(campo, "")):
            resultados[campo]["correctos"] += 1


def predecir_campos(modelo, texto):
    if modelo is None:
        return {}
    entidades = {ent.label_: ent.text for ent in modelo(texto).ents}
    return {campo: entidades.get(etiqueta, "") for campo, etiqueta in ETIQUETAS_CAMPO.items()}


def campo_correcto(campo, esperado, obtenido):
    if campo == "alu_matricula":
        return normalizar_texto(esperado) == normalizar_texto(obtenido)
    return similitud_texto(esperado, obtenido) >= 0.9


def calcular_f1_campos(resultados):
    for datos in resultados.values():
        datos["f1"] = round(datos["correctos"] / datos["total"], 4) if datos["total"] else 0.0
    return resultados


def decidir_activacion(metricas):
    comparacion = comparar_campos(metricas["activo"], metricas["candidato"])
    empeorados = [campo for campo, datos in comparacion.items() if datos["resultado"] == "empeoro"]
    mejorados = [campo for campo, datos in comparacion.items() if datos["resultado"] == "mejoro"]
    activar = not empeorados and bool(mejorados)
    return {"activar": activar, "comparacion": comparacion, "recomendaciones": crear_recomendaciones(empeorados, mejorados)}


def comparar_campos(activo, candidato):
    return {campo: comparar_campo(activo.get(campo, {}), candidato.get(campo, {})) for campo in CAMPOS_OBLIGATORIOS}


def comparar_campo(activo, candidato):
    anterior = float(activo.get("f1", 0))
    nuevo = float(candidato.get("f1", 0))
    return {"f1_anterior": anterior, "f1_candidato": nuevo, "resultado": describir_cambio(anterior, nuevo)}


def describir_cambio(anterior, nuevo):
    if nuevo > anterior:
        return "mejoro"
    if nuevo < anterior:
        return "empeoro"
    return "se_mantiene"


def crear_recomendaciones(empeorados, mejorados):
    if empeorados:
        return [f"Agregar mas ejemplos validados para: {', '.join(empeorados)}"]
    if mejorados:
        return [f"Modelo candidato apto; mejoro: {', '.join(mejorados)}"]
    return ["Agregar mas variedad al lote; ningun campo obligatorio mejoro."]


def normalizar_texto(valor):
    return "".join(str(valor or "").lower().split())


def similitud_texto(esperado, obtenido):
    return SequenceMatcher(None, normalizar_texto(esperado), normalizar_texto(obtenido)).ratio()
