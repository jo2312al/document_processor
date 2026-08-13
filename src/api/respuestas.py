from flask import jsonify


def respuesta_error(mensaje, codigo=400):
    return jsonify({"error": str(mensaje)}), codigo


def respuesta_json(clave, datos, codigo=200):
    return jsonify({clave: datos}), codigo


def respuesta_lista(clave, datos):
    return jsonify({clave: datos}), 200
