CAMPOS_BASE = ["alu_matricula", "NOMBRE_COMPLETO", "alu_carrera", "alu_servicio"]

ETIQUETAS_BASE = {
    "alu_matricula": "MATRICULA",
    "NOMBRE_COMPLETO": "NOMBRE_COMPLETO",
    "alu_carrera": "CARRERA",
    "alu_servicio": "SERVICIO",
}

TIPOS_LEGADOS = {"constancia_servicio"}


def mapa_etiquetas_campos(tipo_documento):
    if usar_campos_base(tipo_documento):
        return dict(ETIQUETAS_BASE)
    mapa = construir_mapa_desde_tipo(tipo_documento)
    return mapa or dict(ETIQUETAS_BASE)


def campos_obligatorios_tipo(tipo_documento):
    if usar_campos_base(tipo_documento):
        return list(CAMPOS_BASE)
    campos = tipo_documento.get("campos", [])
    return [campo["clave"] for campo in campos if campo_valido_obligatorio(campo)]


def campos_evaluables_tipo(tipo_documento):
    obligatorios = campos_obligatorios_tipo(tipo_documento)
    if obligatorios:
        return obligatorios
    return list(mapa_etiquetas_campos(tipo_documento).keys())


def construir_mapa_desde_tipo(tipo_documento):
    mapa = {}
    for campo in tipo_documento.get("campos", []):
        clave = str(campo.get("clave") or "").strip()
        etiqueta = str(campo.get("etiqueta_entidad") or "").strip().upper()
        if clave and etiqueta:
            mapa[clave] = etiqueta
    return mapa


def campo_valido_obligatorio(campo):
    return bool(campo.get("obligatorio") and campo.get("clave"))


def usar_campos_base(tipo_documento):
    id_tipo = str(tipo_documento.get("id_tipo_documento") or "")
    return id_tipo in TIPOS_LEGADOS or not tipo_documento.get("campos")
