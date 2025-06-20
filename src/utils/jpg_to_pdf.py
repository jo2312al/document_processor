from PIL import Image
import os
import logging

# Configuración de logging
logging.basicConfig(filename='../../document_processor.log', level=logging.INFO, 
                    format='%(asctime)s - %(levelname)s - %(message)s')

class JPGToPDFConverter:
    def __init__(self, input_dir='../../generated_images', output_dir='../../generated_pdfs_from_images'):
        self.input_dir = input_dir
        self.output_dir = output_dir
        self.logger = logging.getLogger(__name__)
        os.makedirs(output_dir, exist_ok=True)

    def convert_jpgs_to_pdf(self):
        for filename in os.listdir(self.input_dir):
            if filename.endswith('.jpg'):
                image_path = os.path.join(self.input_dir, filename)
                pdf_path = os.path.join(self.output_dir, f"{filename.replace('.jpg', '')}.pdf")
                image = Image.open(image_path)
                image.save(pdf_path, "PDF", resolution=100.0)
                self.logger.info(f"PDF generado desde imagen: {pdf_path}")

if __name__ == "__main__":
    converter = JPGToPDFConverter()
    converter.convert_jpgs_to_pdf()