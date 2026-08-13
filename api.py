# ==============================================================================
# ARCHIVO: api.py (VersiÃ³n 4 - con Visor PDF)
# ==============================================================================

import os
import sys
import json
import tempfile
import logging
from flask import Flask, request, jsonify, render_template_string
from werkzeug.utils import secure_filename
from pdf2image import convert_from_path

# --- AÃ±adir la ruta del proyecto para poder importar nuestros mÃ³dulos ---
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

# --- Importar la lÃ³gica de predicciÃ³n ---
# AsegÃºrate de que src/processors/predict.py exista y funcione
try:
    from src.processors.predict import predict_entities
    from src.services.gestor_aprendizaje_activo import listar_eventos_revision
    from src.services.gestor_api_keys import (
        ApiKeyInvalida,
        ApiKeySolicitudInvalida,
        generar_api_key,
        listar_api_keys,
        validar_api_key,
    )
    from src.services.gestor_entrenamiento_documentos import (
        DocumentoEntrenamientoInvalido,
        DocumentoEntrenamientoNoEncontrado,
        agregar_anotacion_entrenamiento,
        crear_documento_entrenamiento,
        listar_documentos_entrenamiento,
    )
    from src.services.gestor_preprocesamiento_documental import extraer_texto_documento
    from src.services.gestor_tipos_documento import (
        CatalogoDocumentoInvalido,
        TipoDocumentoNoEncontrado,
        agregar_campo_documento,
        crear_tipo_documento,
        comparar_versiones_modelo,
        listar_tipos_documento,
        registrar_version_modelo,
    )
except ImportError:
    # Fallback por si estas probando el script sin la estructura completa
    class CatalogoDocumentoInvalido(ValueError):
        pass

    class ApiKeyInvalida(ValueError):
        pass

    class ApiKeySolicitudInvalida(ValueError):
        pass

    class TipoDocumentoNoEncontrado(ValueError):
        pass

    class DocumentoEntrenamientoInvalido(ValueError):
        pass

    class DocumentoEntrenamientoNoEncontrado(ValueError):
        pass

    def predict_entities(path, id_tipo_documento=None, metodo_preprocesamiento=None):
        return {"error": "Modulo predict no encontrado", "mock_data": "Datos de prueba"}

    def agregar_campo_documento(id_tipo_documento, datos_campo):
        raise RuntimeError("Modulo gestor no encontrado")

    def agregar_anotacion_entrenamiento(id_documento_entrenamiento, datos_anotacion):
        raise RuntimeError("Modulo gestor de entrenamiento no encontrado")

    def crear_documento_entrenamiento(id_tipo_documento, archivo_origen, nombre_archivo, texto_ocr):
        raise RuntimeError("Modulo gestor de entrenamiento no encontrado")

    def crear_tipo_documento(datos_tipo_documento):
        raise RuntimeError("Modulo gestor no encontrado")

    def listar_tipos_documento():
        return []

    def generar_api_key(datos_api_key):
        raise RuntimeError("Modulo de API keys no encontrado")

    def listar_api_keys():
        return []

    def validar_api_key(api_key, permiso="extract"):
        return True

    def listar_documentos_entrenamiento(id_tipo_documento):
        return []

    def listar_eventos_revision(id_tipo_documento=None):
        return []

    def extraer_texto_documento(pdf_path, tipo_documento=None, metodo_solicitado=None):
        return {"texto": "", "metodo": "no_disponible"}

    def comparar_versiones_modelo(id_tipo_documento, nombre_modelo_candidato):
        raise RuntimeError("Modulo gestor no encontrado")

    def registrar_version_modelo(id_tipo_documento, datos_modelo):
        raise RuntimeError("Modulo gestor no encontrado")
# Importar configuraciÃ³n para los logs (o usar valores por defecto)
try:
    from config import ADMIN_API_TOKEN, LOGS_DIR, LOGGING_FORMAT, LOGGING_LEVEL, POPPLER_PATH
except ImportError:
    LOGS_DIR = os.path.dirname(__file__)
    LOGGING_FORMAT = '%(asctime)s - %(levelname)s - %(message)s'
    LOGGING_LEVEL = 'INFO'
    ADMIN_API_TOKEN = None

# --- ConfiguraciÃ³n de Flask ---
app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = tempfile.gettempdir()
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16 MB

# --- ConfiguraciÃ³n de Logging ---
api_log_file = os.path.join(LOGS_DIR, 'api.log')
logging.basicConfig(
    filename=api_log_file,
    level=getattr(logging, LOGGING_LEVEL, logging.INFO),
    format=LOGGING_FORMAT,
    filemode='a'
)

def validar_token_administrador():
    if not ADMIN_API_TOKEN:
        return False
    return request.headers.get('X-Admin-Token') == ADMIN_API_TOKEN



def obtener_api_key_solicitud():
    auth_header = request.headers.get('Authorization', '')
    if auth_header.lower().startswith('bearer '):
        return auth_header.split(' ', 1)[1].strip()
    return request.headers.get('X-API-Key')


def validar_api_key_cliente():
    try:
        validar_api_key(obtener_api_key_solicitud(), permiso='extract')
        return None
    except ApiKeyInvalida as e:
        return jsonify({"error": str(e)}), 401

def extraer_texto_ocr_entrenamiento(pdf_path, metodo_preprocesamiento=None):
    resultado = extraer_texto_documento(pdf_path, metodo_solicitado=metodo_preprocesamiento)
    return resultado.get("texto", "")

# --- PLANTILLA HTML MEJORADA (Con Visor PDF) ---
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Analizador de Constancias con Visor</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <style>
        .spinner {
            border-top-color: transparent;
            width: 3rem;
            height: 3rem;
            border-radius: 50%;
            border: 4px solid #4f46e5;
            animation: spin 1s linear infinite;
        }
        @keyframes spin {
            to { transform: rotate(360deg); }
        }
        /* Altura personalizada para el visor PDF */
        .pdf-viewer-container {
            height: 75vh;
        }
    </style>
</head>
<body class="bg-gray-900 text-gray-100 min-h-screen p-4">

    <div class="max-w-7xl mx-auto grid grid-cols-1 lg:grid-cols-2 gap-6 h-full">
        
        <div class="bg-gray-800 rounded-lg shadow-lg p-4 flex flex-col">
            <h2 class="text-xl font-bold mb-4 text-indigo-400">1. Documento Original</h2>
            <div class="bg-gray-700 rounded-lg flex-grow border-2 border-dashed border-gray-600 flex items-center justify-center pdf-viewer-container overflow-hidden relative">
                
                <div id="pdf-placeholder" class="text-center text-gray-400 p-6">
                    <svg class="mx-auto h-12 w-12 mb-2 opacity-50" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"></path></svg>
                    <p>El PDF se previsualizarÃ¡ aquÃ­<br>al seleccionarlo.</p>
                </div>

                <iframe id="pdf-frame" class="w-full h-full hidden" src=""></iframe>
            </div>
        </div>

        <div class="bg-gray-800 rounded-lg shadow-lg p-4 flex flex-col h-full">
            <h2 class="text-xl font-bold mb-4 text-indigo-400">2. ExtracciÃ³n de Datos</h2>
            
            <form id="upload-form" class="mb-6">
                <div class="mb-4">
                    <label class="block text-sm font-medium text-gray-300 mb-2">Tipo de documento</label>
                    <select id="tipo-documento" name="id_tipo_documento" class="w-full bg-gray-900 border border-gray-700 rounded-md px-3 py-2 text-gray-100 focus:outline-none focus:ring-2 focus:ring-indigo-500"></select>
                </div>
                <div class="mb-4">
                    <label class="block text-sm font-medium text-gray-300 mb-2">Cargar Archivo</label>
                    <div class="flex items-center space-x-3">
                        <label class="cursor-pointer bg-indigo-600 hover:bg-indigo-700 text-white px-4 py-2 rounded-md font-medium transition-colors">
                            <span>Seleccionar PDF</span>
                            <input id="pdf-file" name="file" type="file" class="hidden" accept=".pdf">
                        </label>
                        <span id="file-name" class="text-gray-400 text-sm truncate">NingÃºn archivo seleccionado</span>
                    </div>
                </div>
                
                <button type="submit" id="submit-btn" class="w-full bg-green-600 hover:bg-green-700 disabled:bg-gray-600 text-white font-bold py-2 px-4 rounded-md transition-colors shadow-md">
                    Analizar Documento
                </button>
            </form>

            <div class="flex-grow flex flex-col min-h-0">
                <h3 class="text-lg font-semibold mb-2 text-gray-300">Resultado JSON:</h3>
                
                <div id="loader" class="hidden flex justify-center items-center py-8">
                    <div class="spinner"></div>
                    <p class="ml-3 text-indigo-300">Procesando con IA...</p>
                </div>

                <div class="relative flex-grow bg-gray-900 rounded-md border border-gray-700 overflow-hidden">
                    <div class="absolute inset-0 overflow-auto p-4 custom-scrollbar">
                        <pre id="results-pre" class="text-xs sm:text-sm font-mono text-green-400 whitespace-pre-wrap"></pre>
                    </div>
                </div>
            </div>
        </div>

    </div>

    <script>
        const fileInput = document.getElementById('pdf-file');
        const fileNameDisplay = document.getElementById('file-name');
        const pdfFrame = document.getElementById('pdf-frame');
        const pdfPlaceholder = document.getElementById('pdf-placeholder');
        const form = document.getElementById('upload-form');
        const loader = document.getElementById('loader');
        const resultsPre = document.getElementById('results-pre');
        const tipoDocumentoSelect = document.getElementById('tipo-documento');

        async function cargarTiposDocumento() {
            const response = await fetch('/tipos-documento');
            const data = await response.json();

            tipoDocumentoSelect.innerHTML = '';
            data.tipos_documento.forEach((tipoDocumento) => {
                const option = document.createElement('option');
                option.value = tipoDocumento.id_tipo_documento;
                option.textContent = tipoDocumento.nombre;
                tipoDocumentoSelect.appendChild(option);
            });
        }

        cargarTiposDocumento().catch(() => {
            const option = document.createElement('option');
            option.value = 'constancia_servicio';
            option.textContent = 'Constancia de servicio';
            tipoDocumentoSelect.appendChild(option);
        });

        // Evento: Al seleccionar archivo
        fileInput.addEventListener('change', function() {
            if (this.files && this.files[0]) {
                const file = this.files[0];
                
                // 1. Actualizar nombre
                fileNameDisplay.textContent = file.name;

                // 2. Crear URL temporal para el navegador (Blob URL)
                const fileURL = URL.createObjectURL(file);
                
                // 3. Mostrar en el iframe
                pdfFrame.src = fileURL;
                pdfFrame.classList.remove('hidden');
                pdfPlaceholder.classList.add('hidden');
            }
        });

        // Evento: Al enviar formulario
        form.addEventListener('submit', async (e) => {
            e.preventDefault();
            
            if (!fileInput.files.length) {
                alert('Por favor, selecciona un archivo PDF primero.');
                return;
            }

            // UI Loading State
            loader.classList.remove('hidden');
            resultsPre.textContent = '';
            
            const formData = new FormData();
            formData.append('file', fileInput.files[0]);
            formData.append('id_tipo_documento', tipoDocumentoSelect.value);

            try {
                const response = await fetch('/extract', {
                    method: 'POST',
                    body: formData,
                });

                const data = await response.json();
                
                if (response.ok) {
                    resultsPre.classList.remove('text-red-400');
                    resultsPre.classList.add('text-green-400');
                    resultsPre.textContent = JSON.stringify(data, null, 2);
                } else {
                    throw new Error(data.error || 'Error desconocido');
                }
            } catch (error) {
                resultsPre.classList.remove('text-green-400');
                resultsPre.classList.add('text-red-400');
                resultsPre.textContent = 'Error: ' + error.message;
            } finally {
                loader.classList.add('hidden');
            }
        });
    </script>
</body>
</html>
"""

@app.route('/', methods=['GET'])
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route('/admin', methods=['GET'])
def admin_panel():
    template_path = os.path.join(os.path.dirname(__file__), 'src', 'templates', 'admin_panel.html')
    with open(template_path, 'r', encoding='utf-8') as template_file:
        return render_template_string(template_file.read())

@app.route('/tipos-documento', methods=['GET'])
def obtener_tipos_documento():
    tipos_documento = listar_tipos_documento()
    return jsonify({
        "tipos_documento": [
            {
                "id_tipo_documento": tipo["id_tipo_documento"],
                "nombre": tipo["nombre"],
                "descripcion": tipo.get("descripcion", ""),
                "estado": tipo.get("estado", "sin_estado"),
                "modelo_activo": tipo.get("modelo_activo"),
                "campos": tipo.get("campos", []),
                "rasgos_documento": tipo.get("rasgos_documento", {}),
                "versiones_modelo": tipo.get("versiones_modelo", []),
            }
            for tipo in tipos_documento
        ]
    }), 200

@app.route('/admin/tipos-documento', methods=['POST'])
def registrar_tipo_documento():
    if not validar_token_administrador():
        return jsonify({"error": "Operacion administrativa no autorizada"}), 401

    datos_tipo_documento = request.get_json(silent=True) or {}
    try:
        tipo_documento = crear_tipo_documento(datos_tipo_documento)
        return jsonify({"tipo_documento": tipo_documento}), 201
    except CatalogoDocumentoInvalido as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        app.logger.error(f"Error registrando tipo de documento: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/admin/tipos-documento/<id_tipo_documento>/campos', methods=['POST'])
def registrar_campo_documento(id_tipo_documento):
    if not validar_token_administrador():
        return jsonify({"error": "Operacion administrativa no autorizada"}), 401

    datos_campo = request.get_json(silent=True) or {}
    try:
        campo = agregar_campo_documento(id_tipo_documento, datos_campo)
        return jsonify({"campo": campo}), 201
    except TipoDocumentoNoEncontrado as e:
        return jsonify({"error": str(e)}), 404
    except CatalogoDocumentoInvalido as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        app.logger.error(f"Error registrando campo documental: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/admin/tipos-documento/<id_tipo_documento>/modelos', methods=['POST'])
def registrar_modelo_documento(id_tipo_documento):
    if not validar_token_administrador():
        return jsonify({"error": "Operacion administrativa no autorizada"}), 401

    datos_modelo = request.get_json(silent=True) or {}
    try:
        version_modelo = registrar_version_modelo(id_tipo_documento, datos_modelo)
        return jsonify({"version_modelo": version_modelo}), 201
    except TipoDocumentoNoEncontrado as e:
        return jsonify({"error": str(e)}), 404
    except CatalogoDocumentoInvalido as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        app.logger.error(f"Error registrando version de modelo: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/admin/tipos-documento/<id_tipo_documento>/modelos/comparar', methods=['GET'])
def comparar_modelo_documento(id_tipo_documento):
    if not validar_token_administrador():
        return jsonify({"error": "Operacion administrativa no autorizada"}), 401

    nombre_candidato = request.args.get("modelo_candidato")
    if not nombre_candidato:
        return jsonify({"error": "modelo_candidato es obligatorio"}), 400

    try:
        comparacion = comparar_versiones_modelo(id_tipo_documento, nombre_candidato)
        return jsonify({"comparacion": comparacion}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 400
@app.route('/admin/tipos-documento/<id_tipo_documento>/documentos-entrenamiento', methods=['GET'])
def obtener_documentos_entrenamiento(id_tipo_documento):
    if not validar_token_administrador():
        return jsonify({"error": "Operacion administrativa no autorizada"}), 401

    documentos = listar_documentos_entrenamiento(id_tipo_documento)
    return jsonify({"documentos_entrenamiento": documentos}), 200

@app.route('/admin/tipos-documento/<id_tipo_documento>/aprendizaje-activo', methods=['GET'])
def obtener_eventos_aprendizaje_activo(id_tipo_documento):
    if not validar_token_administrador():
        return jsonify({"error": "Operacion administrativa no autorizada"}), 401

    eventos = listar_eventos_revision(id_tipo_documento)
    return jsonify({"eventos_revision": eventos}), 200
@app.route('/admin/tipos-documento/<id_tipo_documento>/documentos-entrenamiento', methods=['POST'])
def subir_documento_entrenamiento(id_tipo_documento):
    if not validar_token_administrador():
        return jsonify({"error": "Operacion administrativa no autorizada"}), 401

    if 'file' not in request.files:
        return jsonify({"error": "No se proporciono archivo PDF"}), 400

    file = request.files['file']
    if file.filename == '' or not file.filename.lower().endswith('.pdf'):
        return jsonify({"error": "Solo se aceptan documentos PDF"}), 400

    filename = secure_filename(file.filename)
    temp_pdf_path = os.path.join(app.config['UPLOAD_FOLDER'], f"training_{filename}")

    try:
        file.save(temp_pdf_path)
        texto_ocr = extraer_texto_ocr_entrenamiento(temp_pdf_path, request.form.get('metodo_preprocesamiento'))
        documento = crear_documento_entrenamiento(
            id_tipo_documento,
            temp_pdf_path,
            filename,
            texto_ocr,
        )
        return jsonify({"documento_entrenamiento": documento}), 201
    except DocumentoEntrenamientoInvalido as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        app.logger.error(f"Error subiendo documento de entrenamiento: {e}")
        return jsonify({"error": str(e)}), 500
    finally:
        if os.path.exists(temp_pdf_path):
            os.remove(temp_pdf_path)

@app.route('/admin/documentos-entrenamiento/<id_documento_entrenamiento>/anotaciones', methods=['POST'])
def registrar_anotacion_documento(id_documento_entrenamiento):
    if not validar_token_administrador():
        return jsonify({"error": "Operacion administrativa no autorizada"}), 401

    datos_anotacion = request.get_json(silent=True) or {}
    try:
        anotacion = agregar_anotacion_entrenamiento(
            id_documento_entrenamiento,
            datos_anotacion,
        )
        return jsonify({"anotacion": anotacion}), 201
    except DocumentoEntrenamientoNoEncontrado as e:
        return jsonify({"error": str(e)}), 404
    except DocumentoEntrenamientoInvalido as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        app.logger.error(f"Error registrando anotacion de entrenamiento: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/admin/api-keys', methods=['GET'])
def obtener_api_keys():
    if not validar_token_administrador():
        return jsonify({"error": "Operacion administrativa no autorizada"}), 401

    return jsonify({"api_keys": listar_api_keys()}), 200

@app.route('/admin/api-keys', methods=['POST'])
def crear_api_key():
    if not validar_token_administrador():
        return jsonify({"error": "Operacion administrativa no autorizada"}), 401

    datos_api_key = request.get_json(silent=True) or {}
    try:
        api_key, registro = generar_api_key(datos_api_key)
        return jsonify({"api_key": api_key, "registro": registro}), 201
    except ApiKeySolicitudInvalida as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        app.logger.error(f"Error generando API key: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/extract', methods=['POST'])
def extract_data_from_pdf():
    app.logger.info(f"PeticiÃ³n recibida en /extract")
    
    if 'file' not in request.files:
        return jsonify({"error": "No file part"}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({"error": "No selected file"}), 400

    if file and file.filename.lower().endswith('.pdf'):
        filename = secure_filename(file.filename)
        temp_pdf_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        
        try:
            file.save(temp_pdf_path)
            app.logger.info(f"Procesando: {temp_pdf_path}")
            
            # Llamada a tu lÃ³gica de extracciÃ³n
            id_tipo_documento = request.form.get('id_tipo_documento')
            extracted_data = predict_entities(temp_pdf_path, id_tipo_documento, request.form.get('metodo_preprocesamiento'))
            
            return jsonify(extracted_data), 200

        except Exception as e:
            app.logger.error(f"Error procesando PDF: {e}")
            return jsonify({"error": str(e)}), 500
        finally:
            # Limpieza: Borrar el archivo del servidor
            if os.path.exists(temp_pdf_path):
                os.remove(temp_pdf_path)
                app.logger.info("Archivo temporal eliminado")
    else:
        return jsonify({"error": "Solo archivos PDF"}), 400

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)


















