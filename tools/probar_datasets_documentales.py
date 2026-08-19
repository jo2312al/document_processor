import json
import os
import re
import sys
import tempfile
import time
from contextlib import ExitStack
from datetime import datetime
from unittest.mock import patch

import requests

RAIZ_PROYECTO = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, RAIZ_PROYECTO)

from src.services import entrenador_lotes_aprendizaje as entrenador
from src.services import gestor_lotes_aprendizaje as lotes

API_FILAS = "https://datasets-server.huggingface.co/rows"
SALIDA_BASE = os.path.join("data", "evaluaciones_datasets")
TOTAL_MUESTRAS = 45
EPOCAS_PRUEBA = 20


def main():
    inicio = time.time()
    carpeta = preparar_carpeta_salida()
    resultados = []
    for definicion in datasets_a_probar():
        resultados.append(probar_dataset(definicion, carpeta))
    reporte = crear_reporte(resultados, inicio)
    guardar_reportes(carpeta, reporte)
    imprimir_resumen(reporte)


def probar_dataset(definicion, carpeta):
    inicio = time.time()
    try:
        filas = descargar_filas_seguras(definicion, carpeta)
        guardar_descarga(carpeta, definicion["id"], filas)
        documentos = preparar_documentos(definicion, filas)
        return ejecutar_flujo_usuario(definicion, documentos, inicio)
    except Exception as error:
        return resultado_fallido(definicion, str(error), inicio)


def descargar_filas(definicion):
    parametros = {
        "dataset": definicion["repo"],
        "config": definicion.get("config", "default"),
        "split": definicion.get("split", "train"),
        "offset": 0,
        "length": definicion.get("muestras", TOTAL_MUESTRAS),
    }
    respuesta = requests.get(API_FILAS, params=parametros, timeout=90)
    respuesta.raise_for_status()
    return [fila["row"] for fila in respuesta.json().get("rows", [])]


def descargar_filas_seguras(definicion, carpeta):
    try:
        return descargar_filas(definicion)
    except requests.RequestException:
        filas = cargar_descarga_cache(carpeta, definicion["id"])
        if filas:
            return filas
        raise


def cargar_descarga_cache(carpeta, nombre):
    ruta = os.path.join(carpeta, "descargas", f"{nombre}.json")
    if not os.path.exists(ruta):
        return []
    with open(ruta, "r", encoding="utf-8") as archivo:
        return json.load(archivo)


def preparar_documentos(definicion, filas):
    documentos = []
    for indice, fila in enumerate(filas):
        documento = definicion["transformar"](fila, indice)
        if documento and documento_entrenable(documento, definicion["campos"]):
            documentos.append(documento)
    if len(documentos) < 8:
        raise ValueError(f"Solo hubo {len(documentos)} documentos entrenables.")
    return documentos[: definicion.get("limite_entrenamiento", 30)]


def ejecutar_flujo_usuario(definicion, documentos, inicio):
    preparacion = medir_preparacion(definicion, documentos)
    with tempfile.TemporaryDirectory() as temporal:
        contexto = crear_contexto_temporal(definicion, temporal)
        with aplicar_contexto_prueba(contexto):
            lote = registrar_documentos_como_usuario(definicion, documentos, contexto)
            resultado = entrenador.entrenar_y_evaluar_lote(lote["id_lote"], lotes.obtener_documentos_lote(lote["id_lote"]))
    return resultado_exitoso(definicion, documentos, resultado, preparacion, inicio)


def crear_contexto_temporal(definicion, temporal):
    pdf = os.path.join(temporal, "documento.pdf")
    with open(pdf, "wb") as archivo:
        archivo.write(b"%PDF-1.4\n% prueba dataset\n")
    return {
        "pdf": pdf,
        "estado": os.path.join(temporal, "aprendizaje.json"),
        "validados": os.path.join(temporal, "validados"),
        "modelos": os.path.join(temporal, "modelos"),
        "tipo": crear_tipo_documental(definicion),
    }


def aplicar_contexto_prueba(contexto):
    pila = ExitStack()
    pila.enter_context(patch.object(lotes, "APRENDIZAJE_LOTES_PATH", contexto["estado"]))
    pila.enter_context(patch.object(lotes, "DOCUMENTOS_VALIDADOS_DIR", contexto["validados"]))
    pila.enter_context(patch.object(lotes, "UMBRAL_LOTE_ENTRENAMIENTO", 9999))
    pila.enter_context(patch.object(lotes, "obtener_tipo_documento", lambda _: contexto["tipo"]))
    pila.enter_context(patch.object(entrenador, "MODELS_DIR", contexto["modelos"]))
    pila.enter_context(patch.object(entrenador, "EPOCAS_ENTRENAMIENTO_LOTE", EPOCAS_PRUEBA))
    pila.enter_context(patch.object(entrenador, "obtener_tipo_documento", lambda _: contexto["tipo"]))
    return pila


def registrar_documentos_como_usuario(definicion, documentos, contexto):
    lote_actual = None
    for indice, documento in enumerate(documentos):
        _, lote_actual = lotes.registrar_documento_validado(
            definicion["id"], contexto["pdf"], f"{definicion['id']}_{indice}.pdf", documento["campos"], documento["texto"]
        )
    return lote_actual


def crear_tipo_documental(definicion):
    return {
        "id_tipo_documento": definicion["id"],
        "nombre": definicion["nombre"],
        "modelo_activo": "modelo_activo_no_existente",
        "campos": [crear_campo(clave) for clave in definicion["campos"]],
    }


def crear_campo(clave):
    return {"clave": clave, "etiqueta_entidad": etiqueta_spacy(clave), "tipo": "texto", "obligatorio": True}


def etiqueta_spacy(clave):
    return re.sub(r"[^A-Z0-9]+", "_", clave.upper()).strip("_")


def documento_entrenable(documento, campos):
    texto = documento.get("texto", "")
    valores = [str(documento.get("campos", {}).get(campo, "")).strip() for campo in campos]
    return bool(texto.strip()) and all(valor for valor in valores)


def resultado_exitoso(definicion, documentos, resultado, preparacion, inicio):
    return {
        "dataset": definicion["id"],
        "nombre": definicion["nombre"],
        "fuente": definicion["fuente"],
        "estado": "probado",
        "documentos_usados": len(documentos),
        "segundos": round(time.time() - inicio, 2),
        "preparacion": preparacion,
        "metricas": resultado["metricas"],
        "decision": resultado["decision"],
        "mejora": definicion["mejora"],
    }


def resultado_fallido(definicion, error, inicio):
    return {
        "dataset": definicion["id"],
        "nombre": definicion["nombre"],
        "fuente": definicion["fuente"],
        "estado": "fallo",
        "error": error,
        "segundos": round(time.time() - inicio, 2),
        "mejora": definicion["mejora"],
    }


def guardar_descarga(carpeta, nombre, filas):
    ruta = os.path.join(carpeta, "descargas", f"{nombre}.json")
    os.makedirs(os.path.dirname(ruta), exist_ok=True)
    with open(ruta, "w", encoding="utf-8") as archivo:
        json.dump(filas, archivo, ensure_ascii=False, indent=2)


def crear_reporte(resultados, inicio):
    return {
        "fecha": datetime.now().isoformat(timespec="seconds"),
        "duracion_segundos": round(time.time() - inicio, 2),
        "nota": "Prueba aislada con muestras publicas y flujo equivalente al usuario.",
        "datasets": resultados,
    }


def guardar_reportes(carpeta, reporte):
    ruta_json = os.path.join(carpeta, "reporte_datasets_documentales.json")
    ruta_md = os.path.join(carpeta, "reporte_datasets_documentales.md")
    with open(ruta_json, "w", encoding="utf-8") as archivo:
        json.dump(reporte, archivo, ensure_ascii=False, indent=2)
    with open(ruta_md, "w", encoding="utf-8") as archivo:
        archivo.write(renderizar_markdown(reporte))


def preparar_carpeta_salida():
    os.makedirs(SALIDA_BASE, exist_ok=True)
    return SALIDA_BASE


def imprimir_resumen(reporte):
    print(json.dumps({"duracion": reporte["duracion_segundos"], "datasets": resumen_consola(reporte)}, ensure_ascii=False))


def resumen_consola(reporte):
    return [{k: item.get(k) for k in ["dataset", "estado", "documentos_usados", "segundos", "error"]} for item in reporte["datasets"]]


def renderizar_markdown(reporte):
    lineas = ["# Evaluacion de datasets documentales", "", f"Fecha: {reporte['fecha']}", ""]
    for item in reporte["datasets"]:
        lineas.extend(renderizar_item(item))
    return "\n".join(lineas) + "\n"


def renderizar_item(item):
    lineas = [f"## {item['nombre']}", f"- Estado: {item['estado']}", f"- Fuente: {item['fuente']}"]
    lineas.append(f"- Documentos usados: {item.get('documentos_usados', 0)}")
    lineas.append(f"- Tiempo: {item['segundos']} segundos")
    if item.get("preparacion"):
        lineas.append(f"- Valores localizables en OCR: {item['preparacion']['porcentaje_localizable']}%")
    if item.get("error"):
        lineas.append(f"- Error: {item['error']}")
    lineas.append(f"- Mejora sugerida: {item['mejora']}")
    lineas.extend(renderizar_metricas(item.get("metricas", {})))
    return lineas + [""]


def renderizar_metricas(metricas):
    candidato = metricas.get("candidato", {})
    return [f"- F1 candidato {campo}: {datos.get('f1', 0)}" for campo, datos in candidato.items()]


def medir_preparacion(definicion, documentos):
    total = len(documentos) * len(definicion["campos"])
    localizables = sum(contar_localizables(documento, definicion["campos"]) for documento in documentos)
    porcentaje = round((localizables / total) * 100, 2) if total else 0
    return {"valores": total, "localizables": localizables, "porcentaje_localizable": porcentaje}


def contar_localizables(documento, campos):
    texto = documento.get("texto", "").lower()
    return sum(1 for campo in campos if str(documento["campos"].get(campo, "")).lower() in texto)


def datasets_a_probar():
    return [
        definicion_sroie(),
        definicion_funsd(),
        definicion_katanaml(),
        definicion_feyninc(),
        definicion_charity(),
        definicion_nda(),
        definicion_docvqa(),
    ]


def definicion_sroie():
    return crear_definicion("recibo_sroie", "Recibos SROIE", "tasiam/sroie-2019-v2", ["company", "date", "address", "total"], transformar_sroie, "Normalizar fechas, importes y direcciones para reducir variacion OCR.")


def definicion_funsd():
    return crear_definicion("formulario_funsd", "Formularios FUNSD", "nielsr/funsd", ["header", "question", "answer"], transformar_funsd, "Aprender relaciones etiqueta-respuesta, no solo entidades aisladas.")


def definicion_katanaml():
    return crear_definicion("factura_katanaml", "Facturas Katanaml", "katanaml-org/invoices-donut-data-v1", ["invoice_no", "invoice_date", "seller", "client", "total"], transformar_katanaml, "Agregar validaciones de totales, impuestos y datos fiscales.")


def definicion_feyninc():
    return crear_definicion("factura_feyninc", "Facturas y recibos Feyninc", "feyninc/invoices-and-receipts", ["invoice_no", "date_issue", "seller", "client", "total"], transformar_feyninc, "Separar tablas, encabezados y totales para documentos comerciales.")


def definicion_charity():
    campos = ["charity_name", "charity_number", "report_date", "income", "spending"]
    return crear_definicion("reporte_charity", "Reportes Kleister Charity", "orgrctera/kleister_charity_information_extraction", campos, transformar_kleister, "Mejorar lectura de documentos largos y campos financieros.")


def definicion_nda():
    return crear_definicion("contrato_nda", "Contratos NDA", "orgrctera/kleister_nda_information_extraction", ["effective_date", "jurisdiction", "party", "term"], transformar_kleister, "Agregar soporte para listas de partes y clausulas contractuales.")


def definicion_docvqa():
    return crear_definicion("docvqa_respuesta", "DocVQA documental", "nielsr/docvqa_1200_examples", ["answer"], transformar_docvqa, "Agregar modo pregunta-respuesta sobre documentos.")


def crear_definicion(id_tipo, nombre, repo, campos, transformar, mejora):
    return {"id": id_tipo, "nombre": nombre, "repo": repo, "campos": campos, "transformar": transformar, "fuente": f"https://huggingface.co/datasets/{repo}", "mejora": mejora}


def transformar_sroie(fila, indice):
    objetos = fila.get("objects") or {}
    campos = limpiar_campos(objetos.get("entities") or {})
    texto = "\n".join(objetos.get("text") or [])
    return {"texto": texto, "campos": campos}


def transformar_funsd(fila, indice):
    palabras = fila.get("words") or []
    etiquetas = fila.get("ner_tags") or []
    texto = " ".join(palabras)
    campos = extraer_campos_funsd(palabras, etiquetas)
    return {"texto": texto, "campos": campos}


def extraer_campos_funsd(palabras, etiquetas):
    return {
        "header": extraer_segmento(palabras, etiquetas, {1, 2}),
        "question": extraer_segmento(palabras, etiquetas, {3, 4}),
        "answer": extraer_segmento(palabras, etiquetas, {5, 6}),
    }


def extraer_segmento(palabras, etiquetas, codigos):
    segmentos = []
    actual = []
    for palabra, etiqueta in zip(palabras, etiquetas):
        actual = actual + [palabra] if etiqueta in codigos else cerrar_segmento(segmentos, actual)
    cerrar_segmento(segmentos, actual)
    return max(segmentos, key=len) if segmentos else ""


def cerrar_segmento(segmentos, actual):
    if actual:
        segmentos.append(" ".join(actual))
    return []


def transformar_katanaml(fila, indice):
    datos = json.loads(fila.get("ground_truth", "{}")).get("gt_parse", {})
    encabezado = limpiar_campos(datos.get("header") or {})
    campos = {clave: encabezado.get(clave, "") for clave in ["invoice_no", "invoice_date", "seller", "client"]}
    campos["total"] = extraer_total_katanaml(datos)
    return {"texto": json.dumps(datos, ensure_ascii=False), "campos": campos}


def extraer_total_katanaml(datos):
    resumen = datos.get("summary", {})
    return str(resumen.get("total_gross_worth") or resumen.get("total") or datos.get("total", ""))


def transformar_feyninc(fila, indice):
    texto = fila.get("labels", "")
    campos = {
        "invoice_no": extraer_regex(texto, r"Invoice no:\s*([^\n]+)"),
        "date_issue": extraer_regex(texto, r"Date of issue:\s*([^\n]+)"),
        "seller": extraer_celda_persona(texto, 1),
        "client": extraer_celda_persona(texto, 2),
        "total": extraer_ultimo_total(texto),
    }
    return {"texto": texto, "campos": campos}


def transformar_kleister(fila, indice):
    esperado = fila.get("expected_output") or {}
    if isinstance(esperado, str):
        esperado = json.loads(esperado)
    campos = {clave: primer_valor(esperado.get(clave)) for clave in esperado}
    campos.update(alias_kleister(campos))
    texto = " ".join(f"{clave}: {valor}" for clave, valor in campos.items())
    return {"texto": texto, "campos": campos}


def alias_kleister(campos):
    return {
        "income": campos.get("income_annually_in_british_pounds", ""),
        "spending": campos.get("spending_annually_in_british_pounds", ""),
    }


def transformar_docvqa(fila, indice):
    palabras = fila.get("words") or []
    respuestas = fila.get("answers") or []
    respuesta = str(respuestas[0]).strip() if respuestas else ""
    texto = " ".join(palabras)
    if respuesta.lower() not in texto.lower():
        return None
    return {"texto": texto, "campos": {"answer": respuesta}}


def extraer_regex(texto, patron):
    coincidencia = re.search(patron, texto)
    return coincidencia.group(1).strip() if coincidencia else ""


def extraer_celda_persona(texto, posicion):
    filas = [linea for linea in texto.splitlines() if linea.strip().startswith("|")]
    indice = indice_fila_partes(filas)
    if indice < 0:
        return ""
    celdas = [celda.strip() for celda in filas[indice].split("|") if celda.strip()]
    return celdas[posicion - 1] if len(celdas) >= posicion else ""


def extraer_ultimo_total(texto):
    filas = [linea for linea in texto.splitlines() if "**Total**" in linea]
    if not filas:
        return ""
    totales = re.findall(r"\*\*([^*]+)\*\*", filas[-1])
    return totales[-1].strip() if totales else ""


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


def primer_valor(valor):
    if isinstance(valor, list):
        return str(valor[0]).strip() if valor else ""
    return str(valor or "").strip()


def limpiar_campos(campos):
    return {clave: primer_valor(valor) for clave, valor in campos.items()}


if __name__ == "__main__":
    main()
