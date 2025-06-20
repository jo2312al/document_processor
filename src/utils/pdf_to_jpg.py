from pdf2image import convert_from_path
import os
import logging

# Configuración de logging
logging.basicConfig(filename='../../document_processor.log', level=logging.INFO, 
                    format='%(asctime)s - %(levelname)s - %(message)s')

class PDFToJPGConverter:
    def __init__(self, input_dir='../../generated_docs', output_dir='../../generated_images', poppler_path=r'C:\Program Files\Poppler\Library\bin'):
        self.input_dir = input_dir
        self.output_dir = output_dir
        self.poppler_path = poppler_path
        self.logger = logging.getLogger(__name__)
        os.makedirs(output_dir, exist_ok=True)

    def convert_pdfs_to_jpg(self):
        for filename in os.listdir(self.input_dir):
            if filename.endswith('.pdf'):
                pdf_path = os.path.join(self.input_dir, filename)
                images = convert_from_path(pdf_path, dpi=300, poppler_path=self.poppler_path)
                for i, image in enumerate(images):
                    image_path = os.path.join(self.output_dir, f"{filename.replace('.pdf', '')}_page_{i+1}.jpg")
                    image.save(image_path, 'JPEG')
                    self.logger.info(f"Imagen generada: {image_path}")

if __name__ == "__main__":
    converter = PDFToJPGConverter()
    converter.convert_pdfs_to_jpg()