import pdfplumber
from src.processors.image_processor import ImageProcessor
import logging
import os

# Configuración de logging
logging.basicConfig(filename='document_processor.log', level=logging.INFO, 
                    format='%(asctime)s - %(levelname)s - %(message)s')

class PDFProcessor:
    def __init__(self):
        self.image_processor = ImageProcessor()
        self.logger = logging.getLogger(__name__)

    def process(self, pdf_path):
        # Intentar extraer texto con pdfplumber
        try:
            with pdfplumber.open(pdf_path) as pdf:
                text = ''
                for page in pdf.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text += page_text + '\n'
                if text.strip():
                    self.logger.info("Texto extraído con pdfplumber: %s", text)
                    # Guardar texto extraído para depuración
                    with open('extracted_text.txt', 'w', encoding='utf-8') as f:
                        f.write(text)
                    return text
                else:
                    self.logger.warning("No se pudo extraer texto con pdfplumber, intentando con pdf2image")
        except Exception as e:
            self.logger.error("Error al extraer texto con pdfplumber: %s", str(e))

        # Si pdfplumber falla, usar pdf2image y pytesseract
        try:
            text = self.image_processor.process(pdf_path)
            self.logger.info("Texto extraído con pdf2image y pytesseract: %s", text)
            return text
        except Exception as e:
            self.logger.error("Error al extraer texto con pdf2image: %s", str(e))
            raise Exception(f"No se pudo extraer texto del PDF: {str(e)}")