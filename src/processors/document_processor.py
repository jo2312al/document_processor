from src.processors.pdf_processor import PDFProcessor
from src.processors.text_parser import TextParser
import logging

# Configuración de logging
logging.basicConfig(filename='document_processor.log', level=logging.INFO, 
                    format='%(asctime)s - %(levelname)s - %(message)s')

class DocumentProcessor:
    def __init__(self):
        self.pdf_processor = PDFProcessor()
        self.text_parser = TextParser()
        self.logger = logging.getLogger(__name__)

    def process(self, pdf_path):
        try:
            text = self.pdf_processor.process(pdf_path)
            student_data = self.text_parser.parse(text)
            return student_data
        except Exception as e:
            self.logger.error("Error al procesar el documento: %s", str(e))
            raise