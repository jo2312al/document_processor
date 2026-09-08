import re
from difflib import SequenceMatcher


SUBTIPOS_SERVICIO_SOCIAL = {
    "carta_terminacion_servicio_social": ["carta de terminacion", "carta de terminación"],
    "constancia_liberacion_servicio_social": ["constancia de liberacion", "liberacion de servicio"],
    "carta_aceptacion_servicio_social": ["carta de aceptacion", "carta de aceptación"],
    "solicitud_servicio_social": ["solicitud", "servicio social"],
}


def clasificar_servicio_social(texto):
    texto_normalizado = normalizar_texto(texto)
    puntaje_familia = calcular_puntaje_familia(texto_normalizado)
    subtipo, puntaje_subtipo = detectar_subtipo(texto_normalizado)
    return {
        "familia": "servicio_social" if puntaje_familia >= 0.25 else "desconocida",
        "subtipo": subtipo,
        "confianza": round(max(puntaje_familia, puntaje_subtipo), 4),
    }


def extraer_entidades_servicio_social(texto):
    return limpiar_entidades({
        "MATRICULA": extraer_numero_control(texto),
        "NOMBRE_COMPLETO": extraer_nombre_completo(texto),
        "CARRERA": extraer_carrera(texto),
        "SERVICIO": extraer_periodo(texto),
        "DEPENDENCIA": extraer_dependencia(texto),
        "PROGRAMA": extraer_programa(texto),
        "HORAS": extraer_horas(texto),
        "OFICIO": extraer_oficio(texto),
        "RESPONSABLE": extraer_responsable(texto),
    })


def enriquecer_entidades_servicio_social(texto, entidades):
    entidades_enriquecidas = dict(entidades or {})
    for etiqueta, valor in extraer_entidades_servicio_social(texto).items():
        if debe_usar_valor_contexto(entidades_enriquecidas.get(etiqueta), valor):
            entidades_enriquecidas[etiqueta] = valor
    agregar_nombre_partido(entidades_enriquecidas)
    return entidades_enriquecidas


def debe_usar_valor_contexto(actual, candidato):
    if not candidato:
        return False
    if not actual or actual == "NO ENCONTRADO":
        return True
    return valor_con_ruido(actual) and len(candidato) >= len(str(actual).strip(" .,;:"))


def valor_con_ruido(valor):
    texto = str(valor or "").strip()
    return texto.endswith((",", ".", ";", ":")) or "{" in texto or "|" in texto


def normalizar_texto(texto):
    texto = str(texto or "").lower()
    reemplazos = {"á": "a", "é": "e", "í": "i", "ó": "o", "ú": "u", "ñ": "n"}
    for origen, destino in reemplazos.items():
        texto = texto.replace(origen, destino)
    return re.sub(r"\s+", " ", texto)


def calcular_puntaje_familia(texto):
    pistas = ["servicio social", "numero de control", "carrera", "periodo", "horas"]
    coincidencias = sum(1 for pista in pistas if pista in texto)
    return coincidencias / len(pistas)


def detectar_subtipo(texto):
    candidatos = [(subtipo, similitud_subtipo(texto, frases)) for subtipo, frases in SUBTIPOS_SERVICIO_SOCIAL.items()]
    return max(candidatos, key=lambda item: item[1])


def similitud_subtipo(texto, frases):
    puntajes = [1.0 if frase in texto else SequenceMatcher(None, texto[:120], frase).ratio() for frase in frases]
    return max(puntajes)


def limpiar_entidades(entidades):
    return {etiqueta: limpiar_valor(valor) for etiqueta, valor in entidades.items() if limpiar_valor(valor)}


def limpiar_valor(valor):
    valor = re.sub(r"\s+", " ", str(valor or "")).strip(" .,:;")
    return corregir_ruido_ocr(valor.replace(" | ", " ")).strip()


def corregir_ruido_ocr(valor):
    reemplazos = {"{": "I", "}": "I", "INOUSTRIAL": "INDUSTRIAL", " ALA ": " A LA ", "cerrera": "carrera"}
    for origen, destino in reemplazos.items():
        valor = valor.replace(origen, destino)
    return valor


def extraer_numero_control(texto):
    patrones = [
        r"(?i)(?:numero|n[uú]mero|nimero|nuimero|no\.?)\s+de\s+control(?:\s+escolar)?\D{0,45}([A-Z]?\d{6,10})",
        r"(?i)(?:matricula|matr[ií]cula|cuenta)\D{0,25}([A-Z]?\d{6,10})",
        r"(?i)\bcon\s+([A-Z]?\d{6,10}),\s+de la\s+carrera",
    ]
    return buscar_primer_patron(texto, patrones)


def extraer_nombre_completo(texto):
    patrones = [
        r"(?i)que el\s+(?:C\.?\s+|[^A-ZÁÉÍÓÚÑa-záéíóúñ]{1,4}\s*)?([A-ZÁÉÍÓÚÑa-záéíóúñ\s]{8,90}?)[\.,]+\s+de la",
        r"(?i)al C\.?\s+([A-ZÁÉÍÓÚÑa-záéíóúñ\s]{8,90}?)(?:,\s+con\s+numero|,\s+con\s+número)",
        r"(?i)que el C\.?\s+([A-ZÁÉÍÓÚÑ][A-ZÁÉÍÓÚÑ\s]{8,80}?)[\.,]+\s+de la",
        r"(?i)que e[lt]\s*[\(\{]la[\)\}]\s*C\.?\s+([A-ZÁÉÍÓÚÑa-záéíóúñ\s]{8,80}?)(?:\s+realiz|,|\.)",
        r"(?i)que e[lt]\s*[\(\{]la[\)\}]\s*C\.?\s+([A-ZÁÉÍÓÚÑa-záéíóúñ\s]{8,80}?)(?:\s+de la carrera)",
        r"(?i)que el\s*\(la\)\s*C\.?\s+([A-ZÁÉÍÓÚÑa-záéíóúñ\s]{8,80}?)(?:\s+realiz|,|\.)",
        r"(?i)que,?\s+el C\.?\s+([A-ZÁÉÍÓÚÑa-záéíóúñ\s]{8,80}?)(?:\s+con|\s+de la carrera|,)",
        r"(?i)que\s+la C\.?\s+([A-ZÁÉÍÓÚÑa-záéíóúñ\s]{8,80}?)(?:\s+realiz|,)",
        r"(?i)informo que la C\.?\s+([A-ZÁÉÍÓÚÑa-záéíóúñ\s]{8,80}?)(?:,\s+alumna|\s+alumna)",
        r"(?i)que el C\.?\s+([A-ZÁÉÍÓÚÑa-záéíóúñ\s]{8,80}?)(?:,\s+con|\s+con\s+numero|\s+con\s+número)",
        r"(?i)comunicar que,?\s+el C\.?\s+([A-ZÁÉÍÓÚÑa-záéíóúñ\s]{8,80}?)(?:,\s+con|\s+con\s+numero)",
        r"(?i)asunto[\s\S]{0,80}servicio soci\w+\s+([A-ZÁÉÍÓÚÑ\s]{8,80})\s+MATRICULA",
        r"(?i)nombre\s*(?:del alumno|estudiante)?\s*[:\-]\s*([A-ZÁÉÍÓÚÑa-záéíóúñ\s]{8,80})",
    ]
    return buscar_primer_patron(texto, patrones)


def extraer_carrera(texto):
    patrones = [
        r"(?i)c[ae]rrera de\s+([A-ZÁÉÍÓÚÑa-záéíóúñ\{\}\.\s]{4,90}?)(?:\s+con numero|\s+con número|,|\.)",
        r"(?i)de la carrera\s+de\s+([A-ZÁÉÍÓÚÑa-záéíóúñ\{\}\.\s]{4,90}?)(?:,\s+realiz|\s+realiz|\s+ha|,)",
        r"(?i)de la carrera\s+([A-ZÁÉÍÓÚÑa-záéíóúñ\{\}\.\s]{4,90}?)(?:\s+realiz|\s+ha|,)",
        r"(?i)alumn[ao] de la carrera\s+([A-ZÁÉÍÓÚÑa-záéíóúñ\{\}\.\s]{4,90}?)(?:\s+con|,|\s+ha)",
        r"(?i)estudiante de la\s+([A-ZÁÉÍÓÚÑa-záéíóúñ\s]{8,90}?)(?:,\s+ha|\s+ha|\s+concluy)",
    ]
    return buscar_primer_patron(texto, patrones)


def extraer_dependencia(texto):
    patrones = [
        r"(?i)dependencia\s*:\s*([\s\S]{5,160}?)(?:,\s*en el programa|programa denominado|durante el periodo|\.|\n\n)",
        r"(?i)servicio social en\s+([\s\S]{5,160}?)(?:,\s+participando|,\s+en el programa|\.)",
    ]
    return buscar_primer_patron(texto, patrones)


def extraer_programa(texto):
    patrones = [
        r"(?i)programa denominado\s*:\s*([A-ZÁÉÍÓÚÑa-záéíóúñ\s]{5,120}?)(?:\.|\n)",
        r"(?i)programa\s*:\s*([A-ZÁÉÍÓÚÑa-záéíóúñ\s]{5,120}?)(?:,\s+cubriendo|\.|\n)",
    ]
    return buscar_primer_patron(texto, patrones)


def extraer_periodo(texto):
    patrones = [
        r"(?i)periodo comprendido\s+del\s+([\s\S]{8,120}?\s+al\s+[\s\S]{8,120}?)(?:,\s*obteniendo|,\s*cubriendo)",
        r"(?i)periodo comprendido\s+del\s+([\s\S]{8,120}?\s+al\s+[\s\S]{8,120}?)(?:,\s*acumulando|\.|\n)",
        r"(?i)periodo comprendido\s+de[!l]\s+([\s\S]{8,120}?\s+a[!l]\s+[\s\S]{8,120}?)(?:,\s*acumulando|\.|\n)",
        r"(?i)durante el periodo\s+del\s+([\s\S]{8,120}?\s+al\s+[\s\S]{8,120}?)(?:,\s*acumulando|,\s*cubriendo|\.|\n)",
        r"(?i)periodo de 6 meses,\s+del\s+([\s\S]{8,120}?\s+al\s+[\s\S]{8,120}?)(?:,|\.)",
        r"(?i)a partir del\s+([\s\S]{8,120}?\s+al\s+[\s\S]{8,120}?)(?:,|\.)",
        r"(?i)comprendidos\s+del\s+dia\s+([\s\S]{8,120}?\s+al\s+[\s\S]{8,120}?)(?:\.|\n)",
    ]
    return buscar_primer_patron(texto, patrones)


def extraer_horas(texto):
    return buscar_patron(texto, r"(?i)\b([1-9]\d{2,3})\s*(?:horas|hrs)")


def extraer_oficio(texto):
    patrones = [
        r"(?i)oficio\s+n[uú]m\.?\s*([A-Z0-9/\-]+)",
        r"(?i)no\.\s+de\s+oficio\s*:\s*([A-Z0-9/\-]+)",
    ]
    return buscar_primer_patron(texto, patrones)


def extraer_responsable(texto):
    lineas = [linea.strip() for linea in texto.splitlines() if linea.strip()]
    for indice, linea in enumerate(lineas):
        if "responsable" in linea.lower() and indice > 0:
            return lineas[indice - 1]
    return ""


def buscar_primer_patron(texto, patrones):
    for patron in patrones:
        valor = buscar_patron(texto, patron)
        if valor:
            return valor
    return ""


def buscar_patron(texto, patron):
    coincidencia = re.search(patron, texto or "")
    return coincidencia.group(1) if coincidencia else ""


def agregar_nombre_partido(entidades):
    nombre = entidades.get("NOMBRE_COMPLETO")
    if not nombre:
        return
    partes = nombre.split()
    if len(partes) >= 3:
        entidades.setdefault("NOMBRE", " ".join(partes[:-2]))
        entidades.setdefault("PATERNO", partes[-2])
        entidades.setdefault("MATERNO", partes[-1])
