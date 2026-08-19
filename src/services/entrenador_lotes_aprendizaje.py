import os
import random
import re
from difflib import SequenceMatcher

import spacy
from spacy.training import Example

from config import EPOCAS_ENTRENAMIENTO_LOTE, MODELS_DIR
from src.services.configuracion_campos_documento import campos_evaluables_tipo, mapa_etiquetas_campos
from src.services.gestor_tipos_documento import obtener_ruta_modelo_activo, obtener_tipo_documento

LONGITUD_MAXIMA_TEXTO_ENTRENAMIENTO = 6000
RADIO_CONTEXTO_ENTIDAD = 220


def entrenar_y_evaluar_lote(id_lote, documentos):
    tipo_documento = obtener_tipo_documento(documentos[0]["id_tipo_documento"])
    entrenamiento, validacion = dividir_documentos(documentos)
    ruta_modelo = entrenar_modelo_candidato(tipo_documento, id_lote, entrenamiento)
    metricas = evaluar_modelos(tipo_documento, ruta_modelo, validacion)
    decision = decidir_activacion(tipo_documento, metricas)
    return {"ruta_modelo": ruta_modelo, "metricas": metricas, "decision": decision}


def dividir_documentos(documentos):
    documentos_ordenados = list(documentos)
    random.Random(42).shuffle(documentos_ordenados)
    tamano_validacion = max(1, int(len(documentos_ordenados) * 0.2))
    return documentos_ordenados[tamano_validacion:], documentos_ordenados[:tamano_validacion]


def entrenar_modelo_candidato(tipo_documento, id_lote, documentos):
    nlp = crear_modelo_base()
    ejemplos = crear_ejemplos_entrenamiento(nlp, tipo_documento, documentos)
    entrenar_ejemplos(nlp, ejemplos)
    return guardar_modelo_candidato(nlp, tipo_documento, id_lote)


def crear_modelo_base():
    nlp = spacy.blank("es")
    nlp.add_pipe("ner")
    return nlp


def crear_ejemplos_entrenamiento(nlp, tipo_documento, documentos):
    ejemplos = []
    for documento in documentos:
        ejemplo = crear_ejemplo_documento(nlp, tipo_documento, documento)
        if ejemplo:
            ejemplos.append(ejemplo)
    return ejemplos


def crear_ejemplo_documento(nlp, tipo_documento, documento):
    campos = documento.get("campos_validados", {})
    texto = recortar_texto_entrenamiento(documento.get("texto_ocr", ""), campos)
    entidades = buscar_entidades_validadas(texto, campos, mapa_etiquetas_campos(tipo_documento))
    if not entidades:
        return None
    return crear_ejemplo_alineado(nlp, texto, entidades)


def recortar_texto_entrenamiento(texto, campos):
    if len(texto) <= LONGITUD_MAXIMA_TEXTO_ENTRENAMIENTO:
        return texto
    fragmentos = crear_fragmentos_entrenamiento(texto, campos)
    return "\n".join(fragmentos) if fragmentos else texto[:LONGITUD_MAXIMA_TEXTO_ENTRENAMIENTO]


def crear_fragmentos_entrenamiento(texto, campos):
    fragmentos = []
    for valor in campos.values():
        fragmento = extraer_fragmento_valor(texto, valor)
        if fragmento and fragmento not in fragmentos:
            fragmentos.append(fragmento)
    return fragmentos


def extraer_fragmento_valor(texto, valor):
    valor = str(valor or "").strip()
    inicio = texto.lower().find(valor.lower())
    if inicio < 0:
        return ""
    desde = max(0, inicio - RADIO_CONTEXTO_ENTIDAD)
    hasta = min(len(texto), inicio + len(valor) + RADIO_CONTEXTO_ENTIDAD)
    return texto[desde:hasta]


def crear_ejemplo_alineado(nlp, texto, entidades):
    prediccion = nlp.make_doc(texto)
    referencia = nlp.make_doc(texto)
    referencia.ents = crear_spans_alineados(referencia, entidades)
    if not referencia.ents:
        return None
    return Example(prediccion, referencia)


def crear_spans_alineados(doc, entidades):
    spans = []
    for inicio, fin, etiqueta in entidades:
        span = doc.char_span(inicio, fin, label=etiqueta, alignment_mode="expand")
        if span:
            spans.append(span)
    return filtrar_spans_traslapados(spans)


def filtrar_spans_traslapados(spans):
    spans_ordenados = sorted(spans, key=lambda span: (span.start, -(span.end - span.start)))
    seleccionados = []
    ultimo_fin = -1
    for span in spans_ordenados:
        if span.start >= ultimo_fin:
            seleccionados.append(span)
            ultimo_fin = span.end
    return seleccionados


def buscar_entidades_validadas(texto, campos, mapa_etiquetas):
    entidades = []
    for clave, etiqueta in mapa_etiquetas.items():
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
    return {
        "activo": evaluar_modelo(modelo_activo, tipo_documento, documentos),
        "candidato": evaluar_modelo(modelo_candidato, tipo_documento, documentos),
    }


def cargar_modelo_seguro(ruta_modelo):
    if not os.path.exists(ruta_modelo):
        return None
    return spacy.load(ruta_modelo)


def evaluar_modelo(modelo, tipo_documento, documentos):
    campos = campos_evaluables_tipo(tipo_documento)
    resultados = {campo: {"correctos": 0, "total": 0, "f1": 0.0} for campo in campos}
    for documento in documentos:
        evaluar_documento(modelo, tipo_documento, documento, resultados)
    return calcular_f1_campos(resultados)


def evaluar_documento(modelo, tipo_documento, documento, resultados):
    texto = documento.get("texto_ocr", "")
    predicciones = predecir_campos(modelo, texto, mapa_etiquetas_campos(tipo_documento))
    for campo in resultados:
        esperado = documento.get("campos_validados", {}).get(campo, "")
        resultados[campo]["total"] += 1
        if campo_correcto(campo, esperado, predicciones.get(campo, "")):
            resultados[campo]["correctos"] += 1


def predecir_campos(modelo, texto, mapa_etiquetas):
    if modelo is None:
        return {campo: extraer_por_contexto(texto, campo) for campo in mapa_etiquetas}
    entidades = {ent.label_: ent.text for ent in modelo(texto).ents}
    return {campo: elegir_prediccion(texto, campo, entidades.get(etiqueta, "")) for campo, etiqueta in mapa_etiquetas.items()}


def elegir_prediccion(texto, campo, valor_modelo):
    valor_contexto = extraer_por_contexto(texto, campo)
    if valor_contexto:
        return valor_contexto
    return valor_modelo


def extraer_por_contexto(texto, campo):
    valor_especial = extraer_campo_especial(texto, campo)
    if valor_especial:
        return valor_especial
    for etiqueta in etiquetas_contexto(campo):
        valor = extraer_valor_etiquetado(texto, etiqueta)
        if valor:
            return valor
    return ""


def extraer_campo_especial(texto, campo):
    extractores = {
        "total": extraer_total_documento,
        "seller": lambda valor: extraer_tabla_partes(valor, 1),
        "client": lambda valor: extraer_tabla_partes(valor, 2),
    }
    extractor = extractores.get(str(campo or "").lower())
    return extractor(texto) if extractor else ""


def etiquetas_contexto(campo):
    base = str(campo or "").strip()
    variantes = {base, base.replace("_", " "), base.replace("_", "-")}
    variantes.add(re.sub(r"(?<!^)([A-Z])", r" \1", base).lower())
    variantes.update(alias_campos_contexto().get(base.lower(), []))
    return [variante for variante in variantes if variante]


def alias_campos_contexto():
    return {
        "date_issue": ["date of issue", "issue date"],
        "invoice_date": ["invoice date", "date of issue"],
        "invoice_no": ["invoice no", "invoice number"],
        "charity_number": ["charity number"],
        "charity_name": ["charity name"],
        "report_date": ["report date"],
    }


def extraer_valor_etiquetado(texto, etiqueta):
    valor_json = extraer_valor_json(texto, etiqueta)
    if valor_json:
        return valor_json
    patron = rf"(?i)(?:^|[\n\r,{{|#\s])(?:\"?\*?\*?{re.escape(etiqueta)}\"?\*?\*?)\s*(?:[:=]|\|)\s*\"?([^\"\n\r,|}}]+)"
    coincidencia = re.search(patron, texto)
    if not coincidencia:
        return ""
    return limpiar_valor_contexto(coincidencia.group(1))


def extraer_valor_json(texto, etiqueta):
    patron = rf'(?i)"{re.escape(etiqueta)}"\s*:\s*"([^"]+)"'
    coincidencia = re.search(patron, texto)
    return limpiar_valor_contexto(coincidencia.group(1)) if coincidencia else ""


def limpiar_valor_contexto(valor):
    valor_limpio = str(valor or "").replace("**", "").replace("<br>", " ")
    valor_limpio = re.split(r"\s+[A-Za-z][A-Za-z0-9_]{2,}\s*:", valor_limpio, maxsplit=1)[0]
    return valor_limpio.strip(" -:\t")


def extraer_total_documento(texto):
    total_json = extraer_valor_etiquetado(texto, "total_gross_worth")
    if total_json:
        return total_json
    total_tabla = extraer_total_tabla(texto)
    return total_tabla or extraer_valor_etiquetado(texto, "total")


def extraer_total_tabla(texto):
    filas_total = [linea for linea in texto.splitlines() if "total" in linea.lower()]
    if not filas_total:
        return ""
    celdas = [limpiar_valor_contexto(celda) for celda in filas_total[-1].split("|")]
    celdas = [celda for celda in celdas if celda and celda.lower() != "total"]
    return celdas[-1] if celdas else ""


def extraer_tabla_partes(texto, posicion):
    filas = [linea for linea in texto.splitlines() if linea.strip().startswith("|")]
    indice = indice_fila_partes(filas)
    if indice < 0:
        return ""
    celdas = [celda.strip() for celda in filas[indice].split("|") if celda.strip()]
    return celdas[posicion - 1] if len(celdas) >= posicion else ""


def indice_fila_partes(filas):
    for indice, fila in enumerate(filas):
        if "seller" in fila.lower() and "client" in fila.lower():
            return siguiente_fila_datos(filas, indice + 1)
    return -1


def siguiente_fila_datos(filas, inicio):
    for indice in range(inicio, len(filas)):
        if "---" not in filas[indice]:
            return indice
    return -1


def campo_correcto(campo, esperado, obtenido):
    if not str(esperado or "").strip():
        return not str(obtenido or "").strip()
    if es_campo_fecha(campo, esperado):
        return normalizar_fecha(esperado) == normalizar_fecha(obtenido)
    if es_campo_importe(campo, esperado):
        return normalizar_importe(esperado) == normalizar_importe(obtenido)
    if campo in ["alu_matricula", "matricula", "numero_control"]:
        return normalizar_texto(esperado) == normalizar_texto(obtenido)
    return similitud_texto(esperado, obtenido) >= umbral_similitud(campo, esperado)


def es_campo_fecha(campo, valor):
    return "date" in str(campo).lower() or "fecha" in str(campo).lower() or bool(extraer_fecha(valor))


def es_campo_importe(campo, valor):
    clave = str(campo).lower()
    pistas = ["total", "income", "spending", "amount", "price", "worth", "tax", "importe"]
    return any(pista in clave for pista in pistas) or bool(extraer_importe(valor))


def normalizar_fecha(valor):
    fecha = extraer_fecha(valor)
    return "-".join(fecha) if fecha else normalizar_texto(valor)


def extraer_fecha(valor):
    texto = str(valor or "")
    formatos = [r"\b(\d{4})-(\d{1,2})-(\d{1,2})\b", r"\b(\d{1,2})/(\d{1,2})/(\d{2,4})\b"]
    for indice, patron in enumerate(formatos):
        coincidencia = re.search(patron, texto)
        if coincidencia:
            return ordenar_fecha(coincidencia.groups(), indice)
    return None


def ordenar_fecha(partes, indice_formato):
    if indice_formato == 0:
        ano, mes, dia = partes
    else:
        mes, dia, ano = partes
    ano = f"20{ano}" if len(ano) == 2 else ano
    return ano.zfill(4), mes.zfill(2), dia.zfill(2)


def normalizar_importe(valor):
    importe = extraer_importe(valor)
    if importe is None:
        return normalizar_texto(valor)
    return f"{importe:.2f}"


def extraer_importe(valor):
    numeros = re.findall(r"[-+]?\d[\d.,]*", str(valor or ""))
    if not numeros:
        return None
    return convertir_importe(numeros[-1])


def convertir_importe(valor):
    texto = str(valor).replace(" ", "")
    texto = texto.replace(",", ".") if texto.count(",") == 1 and texto.count(".") == 0 else texto.replace(",", "")
    try:
        return float(texto)
    except ValueError:
        return None


def umbral_similitud(campo, esperado):
    if len(normalizar_texto(esperado)) > 35:
        return 0.75
    if str(campo).lower() in ["seller", "client", "address", "company"]:
        return 0.8
    return 0.9


def calcular_f1_campos(resultados):
    for datos in resultados.values():
        datos["f1"] = round(datos["correctos"] / datos["total"], 4) if datos["total"] else 0.0
    return resultados


def decidir_activacion(tipo_documento, metricas):
    campos = campos_evaluables_tipo(tipo_documento)
    comparacion = comparar_campos(metricas["activo"], metricas["candidato"], campos)
    empeorados = [campo for campo, datos in comparacion.items() if datos["resultado"] == "empeoro"]
    mejorados = [campo for campo, datos in comparacion.items() if datos["resultado"] == "mejoro"]
    activar = not empeorados and bool(mejorados)
    return {"activar": activar, "comparacion": comparacion, "recomendaciones": crear_recomendaciones(empeorados, mejorados)}


def comparar_campos(activo, candidato, campos):
    return {campo: comparar_campo(activo.get(campo, {}), candidato.get(campo, {})) for campo in campos}


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
    texto = str(valor or "").lower().replace("<br>", " ").replace("_", " ")
    texto = re.sub(r"[^a-z0-9áéíóúñ]+", "", texto)
    return texto


def similitud_texto(esperado, obtenido):
    return SequenceMatcher(None, normalizar_texto(esperado), normalizar_texto(obtenido)).ratio()
