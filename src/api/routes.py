from flask import request, jsonify
from src.processors.document_processor import DocumentProcessor
import os
import logging
import json

logging.basicConfig(filename='document_processor.log', level=logging.INFO, 
                    format='%(asctime)s - %(levelname)s - %(message)s')

def init_routes(app):
    @app.route('/process-document', methods=['POST'])
    def process_document():
        logger = logging.getLogger(__name__)
        
        if 'file' not in request.files:
            logger.error("No se proporcionó archivo")
            return jsonify({'error_message': 'No file provided'}), 400

        file = request.files['file']
        if file.filename == '':
            logger.error("No se seleccionó archivo")
            return jsonify({'error_message': 'No file selected'}), 400

        if not file.filename.lower().endswith('.pdf'):
            logger.error("Formato de archivo no soportado: %s", file.filename)
            return jsonify({'error_message': 'Only PDF files are supported'}), 400

        # Guardar archivo temporalmente
        os.makedirs('uploads', exist_ok=True)
        file_path = os.path.join('uploads', file.filename)
        file.save(file_path)
        logger.info("Archivo guardado: %s", file_path)

        try:
            processor = DocumentProcessor()
            student_data = processor.process(file_path)
            student_data['filename'] = file.filename
            logger.info("Datos procesados: %s", student_data)
            # Asegurar codificación UTF-8 y formato legible en la respuesta JSON
            return app.response_class(
                response=json.dumps(student_data, ensure_ascii=False, indent=2),
                status=200,
                mimetype='application/json; charset=utf-8'
            )
        except Exception as e:
            logger.error("Error procesando archivo: %s", str(e))
            # Formatear error en JSON legible
            return app.response_class(
                response=json.dumps({'error_message': str(e)}, ensure_ascii=False, indent=2),
                status=500,
                mimetype='application/json; charset=utf-8'
            )
        finally:
            if os.path.exists(file_path):
                os.remove(file_path)
                logger.info("Archivo temporal eliminado: %s", file_path)