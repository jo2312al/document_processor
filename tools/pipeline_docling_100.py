import json
import os
import re
import time
from pathlib import Path

from docling.document_converter import DocumentConverter
from thefuzz import fuzz
from tqdm import tqdm

from config import DATA_DIR, GENERATED_DOCS_DIR, LABELS_DIR


def cargar_etiquetas():
    etiquetas = {}
    for ruta in Path(LABELS_DIR).glob("*.json"):
        clave = ruta.stem.replace("labels_", "")
        etiquetas[clave] = json.loads(ruta.read_text(encoding="utf-8"))["fields"]
    return etiquetas


def encontrar_coincidencia(texto_ocr, valor, minimo=85):
    if not valor or not texto_ocr:
        return None
    palabras_valor = valor.split()
    palabras_ocr = [(m.group(0), m.start()) for m in re.finditer(r"\S+", texto_ocr)]
    return buscar_mejor_rango(palabras_ocr, palabras_valor, valor, minimo)


def buscar_mejor_rango(palabras_ocr, palabras_valor, valor, minimo):
    mejor = (0, None)
    for indice in range(len(palabras_ocr) - len(palabras_valor) + 1):
        frase = " ".join(palabra for palabra, _ in palabras_ocr[indice:indice + len(palabras_valor)])
        puntaje = fuzz.ratio(valor.lower(), frase.lower())
        mejor = elegir_mejor_rango(mejor, palabras_ocr, indice, len(palabras_valor), puntaje)
    return mejor[1] if mejor[0] >= minimo else None


def elegir_mejor_rango(mejor, palabras_ocr, indice, total_palabras, puntaje):
    if puntaje <= mejor[0]:
        return mejor
    inicio = palabras_ocr[indice][1]
    ultima = palabras_ocr[indice + total_palabras - 1]
    return puntaje, (inicio, ultima[1] + len(ultima[0]), puntaje)


def resolver_solapamientos(entidades):
    entidades.sort(key=lambda entidad: entidad["score"], reverse=True)
    aceptadas, rangos = [], []
    for entidad in entidades:
        if not tiene_solapamiento(entidad, rangos):
            aceptadas.append((entidad["start"], entidad["end"], entidad["label"]))
            rangos.append((entidad["start"], entidad["end"]))
    return aceptadas


def tiene_solapamiento(entidad, rangos):
    return any(max(entidad["start"], ini) < min(entidad["end"], fin) for ini, fin in rangos)


def convertir_pdf(conversor, ruta_pdf):
    resultado = conversor.convert(str(ruta_pdf))
    return resultado.document.export_to_markdown()


def alinear_documento(texto, campos):
    candidatas = []
    for clave, datos in campos.items():
        valor = datos.get("value", "").strip()
        match = encontrar_coincidencia(texto, valor)
        if match:
            candidatas.append(crear_entidad(clave, match))
    entidades = resolver_solapamientos(candidatas)
    return (texto, {"entities": entidades}) if entidades else None


def crear_entidad(clave, match):
    inicio, fin, puntaje = match
    return {"start": inicio, "end": fin, "label": clave.upper(), "score": puntaje}


def procesar_lote(limite=100):
    etiquetas = cargar_etiquetas()
    conversor = DocumentConverter()
    documentos = list(Path(GENERATED_DOCS_DIR).glob("*.pdf"))[:limite]
    return procesar_documentos(conversor, documentos, etiquetas)


def procesar_documentos(conversor, documentos, etiquetas):
    ejemplos, errores = [], []
    for ruta_pdf in tqdm(documentos, desc="Docling OCR y alineacion"):
        resultado = procesar_documento(conversor, ruta_pdf, etiquetas)
        registrar_resultado(resultado, ejemplos, errores)
    return ejemplos, errores


def procesar_documento(conversor, ruta_pdf, etiquetas):
    campos = etiquetas.get(ruta_pdf.stem)
    if not campos:
        return {"archivo": ruta_pdf.name, "error": "sin_etiquetas"}
    try:
        texto = convertir_pdf(conversor, ruta_pdf)
        ejemplo = alinear_documento(texto, campos)
        return {"archivo": ruta_pdf.name, "ejemplo": ejemplo}
    except Exception as exc:
        return {"archivo": ruta_pdf.name, "error": str(exc)}


def registrar_resultado(resultado, ejemplos, errores):
    if resultado.get("ejemplo"):
        ejemplos.append(resultado["ejemplo"])
    else:
        errores.append({"archivo": resultado["archivo"], "error": resultado.get("error", "sin_entidades")})


def guardar_resultados(ejemplos, errores, segundos):
    salida = Path(DATA_DIR) / "spacy_training_data_docling.json"
    resumen = Path(DATA_DIR) / "resumen_docling_100.json"
    salida.write_text(json.dumps(ejemplos, ensure_ascii=False, indent=2), encoding="utf-8")
    resumen.write_text(json.dumps(crear_resumen(ejemplos, errores, segundos), ensure_ascii=False, indent=2), encoding="utf-8")


def crear_resumen(ejemplos, errores, segundos):
    return {
        "metodo": "docling",
        "segundos": round(segundos, 2),
        "minutos": round(segundos / 60, 2),
        "ejemplos_validos": len(ejemplos),
        "documentos_fallidos": len(errores),
        "errores": errores[:20],
    }


def main():
    inicio = time.perf_counter()
    ejemplos, errores = procesar_lote(100)
    guardar_resultados(ejemplos, errores, time.perf_counter() - inicio)
    print(json.dumps(crear_resumen(ejemplos, errores, time.perf_counter() - inicio), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
