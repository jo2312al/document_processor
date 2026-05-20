# ==============================================================================
# ARCHIVO: api.py (Versión 4 - con Visor PDF)
# ==============================================================================

import os
import sys
import json
import tempfile
import logging
from flask import Flask, request, jsonify, render_template_string
from werkzeug.utils import secure_filename

# --- Añadir la ruta del proyecto para poder importar nuestros módulos ---
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

# --- Importar la lógica de predicción ---
# Asegúrate de que src/processors/predict.py exista y funcione
try:
    from src.processors.predict import predict_entities
except ImportError:
    # Fallback por si estás probando el script sin la estructura completa
    def predict_entities(path):
        return {"error": "Módulo predict no encontrado", "mock_data": "Datos de prueba"}

# Importar configuración para los logs (o usar valores por defecto)
try:
    from config import LOGS_DIR, LOGGING_FORMAT, LOGGING_LEVEL
except ImportError:
    LOGS_DIR = os.path.dirname(__file__)
    LOGGING_FORMAT = '%(asctime)s - %(levelname)s - %(message)s'
    LOGGING_LEVEL = 'INFO'

# --- Configuración de Flask ---
app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = tempfile.gettempdir()
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16 MB

# --- Configuración de Logging ---
api_log_file = os.path.join(LOGS_DIR, 'api.log')
logging.basicConfig(
    filename=api_log_file,
    level=getattr(logging, LOGGING_LEVEL, logging.INFO),
    format=LOGGING_FORMAT,
    filemode='a'
)

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
                    <p>El PDF se previsualizará aquí<br>al seleccionarlo.</p>
                </div>

                <iframe id="pdf-frame" class="w-full h-full hidden" src=""></iframe>
            </div>
        </div>

        <div class="bg-gray-800 rounded-lg shadow-lg p-4 flex flex-col h-full">
            <h2 class="text-xl font-bold mb-4 text-indigo-400">2. Extracción de Datos</h2>
            
            <form id="upload-form" class="mb-6">
                <div class="mb-4">
                    <label class="block text-sm font-medium text-gray-300 mb-2">Cargar Archivo</label>
                    <div class="flex items-center space-x-3">
                        <label class="cursor-pointer bg-indigo-600 hover:bg-indigo-700 text-white px-4 py-2 rounded-md font-medium transition-colors">
                            <span>Seleccionar PDF</span>
                            <input id="pdf-file" name="file" type="file" class="hidden" accept=".pdf">
                        </label>
                        <span id="file-name" class="text-gray-400 text-sm truncate">Ningún archivo seleccionado</span>
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

@app.route('/extract', methods=['POST'])
def extract_data_from_pdf():
    app.logger.info(f"Petición recibida en /extract")
    
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
            
            # Llamada a tu lógica de extracción
            extracted_data = predict_entities(temp_pdf_path)
            
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