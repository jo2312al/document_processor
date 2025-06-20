import os
import shutil
import random
import cv2
import numpy as np
from pdf2image import convert_from_path
from PIL import Image
import logging
import psutil
import sys
import argparse
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))
from config import BASE_DIR, LOGS_DIR, LOGGING_FORMAT, LOGGING_LEVEL

# Definir rutas
INPUT_DIR = os.path.join(BASE_DIR, 'generated_docs')
OUTPUT_DIR = os.path.join(BASE_DIR, 'generated_images')
LOG_FILE = os.path.join(LOGS_DIR, 'image_processor.log')

# Crear directorios
os.makedirs(LOGS_DIR, exist_ok=True)
os.makedirs(OUTPUT_DIR, exist_ok=True)

# Configurar logging
logging.basicConfig(
    filename=LOG_FILE,
    level=getattr(logging, LOGGING_LEVEL),
    format=LOGGING_FORMAT,
    force=True,
    filemode='w'
)
logger = logging.getLogger(__name__)
logger.debug("Logging configurado correctamente")

class ImageProcessor:
    def __init__(self, input_dir=INPUT_DIR, output_dir=OUTPUT_DIR):
        self.input_dir = input_dir
        self.output_dir = output_dir
        self.logger = logging.getLogger(__name__)
        self.poppler_path = r'C:\Program Files\Poppler\Library\bin'  # Ajusta si es necesario
        self.logger.debug(f"Inicializando con poppler_path={self.poppler_path}")
        
        # Verificar input_dir
        if not os.path.exists(self.input_dir):
            self.logger.error(f"Directorio {self.input_dir} no existe")
            raise FileNotFoundError(f"Directorio {self.input_dir} no existe")
        self.logger.debug(f"Directorio {self.input_dir} existe")

        # Verificar permisos de escritura en output_dir
        try:
            if os.path.exists(self.output_dir):
                test_file = os.path.join(self.output_dir, "test.txt")
                with open(test_file, 'w') as f:
                    f.write("test")
                os.remove(test_file)
                self.logger.debug(f"Permisos de escritura confirmados en {self.output_dir}")
            else:
                os.makedirs(self.output_dir, exist_ok=True)
                self.logger.debug(f"Carpeta {self.output_dir} creada para verificar permisos")
        except Exception as e:
            self.logger.error(f"Error de permisos en {self.output_dir}: {str(e)}")
            raise

        # Verificar espacio en disco
        disk = psutil.disk_usage(os.path.dirname(self.output_dir))
        free_mb = disk.free / (1024 * 1024)
        self.logger.debug(f"Espacio libre en disco: {free_mb:.2f} MB")
        if free_mb < 1000:
            self.logger.warning(f"Espacio en disco bajo: {free_mb:.2f} MB")

        # Borrar carpeta de imágenes si existe
        try:
            if os.path.exists(self.output_dir):
                shutil.rmtree(self.output_dir)
                self.logger.info(f"Carpeta {self.output_dir} eliminada")
            os.makedirs(self.output_dir, exist_ok=True)
            self.logger.info(f"Carpeta {self.output_dir} creada")
        except Exception as e:
            self.logger.error(f"Error al borrar/crear {self.output_dir}: {str(e)}")
            raise

    def add_noise(self, image, mean=0, sigma=3):
        self.logger.debug(f"Añadiendo ruido gaussiano (shape={image.shape})")
        try:
            if image.size == 0:
                self.logger.error("Imagen vacía, omitiendo add_noise")
                raise ValueError("Imagen vacía")
            gauss = np.random.normal(mean, sigma, image.shape).astype(np.uint8)
            self.logger.debug(f"Ruido generado (shape={gauss.shape})")
            if gauss.shape != image.shape:
                self.logger.error(f"Dimensiones incompatibles: image={image.shape}, gauss={gauss.shape}")
                raise ValueError("Dimensiones incompatibles")
            noisy = cv2.add(image, gauss)
            result = np.clip(noisy, 0, 255)
            self.logger.debug(f"Ruido añadido correctamente (shape={result.shape})")
            return result
        except Exception as e:
            self.logger.error(f"Error en add_noise: {str(e)}")
            raise

    def preprocess_image(self, image, quality_level):
        self.logger.debug(f"Preprocesando imagen con calidad {quality_level}")
        try:
            image = np.array(image)
            self.logger.debug(f"Imagen convertida a array (shape={image.shape})")
            if image.size == 0:
                self.logger.error("Imagen vacía, omitiendo preprocess_image")
                raise ValueError("Imagen vacía")
            gray = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)
            self.logger.debug(f"Convertida a escala de grises (shape={gray.shape})")
            
            if quality_level == 'low':
                gray = cv2.GaussianBlur(gray, (3, 3), 0)
                self.logger.debug("Aplicado desenfoque (calidad baja)")
                gray = self.add_noise(gray)
            elif quality_level == 'medium':
                gray = cv2.GaussianBlur(gray, (1, 1), 0)
                self.logger.debug("Aplicado desenfoque (calidad media)")
            
            _, thresh = cv2.threshold(gray, 180, 255, cv2.THRESH_BINARY)
            self.logger.debug("Aplicada umbralización")
            
            angle = random.uniform(-2, 2)
            M = cv2.getRotationMatrix2D((gray.shape[1]/2, gray.shape[0]/2), angle, 1)
            thresh = cv2.warpAffine(thresh, M, (gray.shape[1], gray.shape[0]))
            self.logger.debug(f"Aplicada rotación ({angle:.2f} grados)")
            
            result = Image.fromarray(thresh)
            self.logger.debug("Imagen procesada convertida a PIL")
            return result
        except Exception as e:
            self.logger.error(f"Error en preprocess_image: {str(e)}")
            raise

    def process_pdfs(self, num_pdfs=None):
        quality_levels = ['high', 'medium', 'low']
        dpi_settings = {'high': 215, 'medium': 165, 'low': 115}
        
        pdf_files = [f for f in os.listdir(self.input_dir) if f.endswith('.pdf')]
        self.logger.info(f"Encontrados {len(pdf_files)} PDFs en {self.input_dir}: {pdf_files[:5]}...")
        
        if not pdf_files:
            self.logger.warning(f"No se encontraron PDFs en {self.input_dir}")
            return

        # Seleccionar PDFs según num_pdfs
        if num_pdfs is not None and num_pdfs > 0:
            pdf_files = random.sample(pdf_files, min(num_pdfs, len(pdf_files)))
            self.logger.info(f"Procesando {len(pdf_files)} PDFs (seleccionados de {num_pdfs} solicitados)")
        else:
            self.logger.info(f"Procesando todos los {len(pdf_files)} PDFs")

        for pdf_file in pdf_files:
            quality = random.choice(quality_levels)
            dpi = dpi_settings[quality]
            pdf_path = os.path.join(self.input_dir, pdf_file)
            self.logger.debug(f"Procesando PDF: {pdf_path} (Calidad: {quality}, DPI: {dpi})")
            
            try:
                images = convert_from_path(
                    pdf_path,
                    dpi=dpi,
                    poppler_path=self.poppler_path if os.path.exists(self.poppler_path) else None
                )
                self.logger.debug(f"Convertido {pdf_file} a {len(images)} imágenes")
                
                for i, image in enumerate(images):
                    try:
                        processed_image = self.preprocess_image(image, quality)
                        base_name = pdf_file.split('.')[0]
                        output_path = os.path.join(self.output_dir, f"{base_name}_page_{i+1}.jpg")
                        self.logger.debug(f"Guardando imagen en {output_path}")
                        processed_image.save(output_path, quality=95)
                        self.logger.info(f"Imagen generada: {output_path} (Calidad: {quality}, DPI: {dpi})")
                    except Exception as e:
                        self.logger.error(f"Error al procesar página {i+1} de {pdf_file}: {str(e)}")
                        continue
            except Exception as e:
                self.logger.error(f"Error procesando {pdf_file}: {str(e)}")
                continue

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Procesa PDFs a imágenes.")
    parser.add_argument("--num_pdfs", type=int, default=None, help="Número de PDFs a procesar (opcional, procesa todos si no se especifica)")
    args = parser.parse_args()
    
    try:
        processor = ImageProcessor()
        processor.process_pdfs(num_pdfs=args.num_pdfs)
    except Exception as e:
        logger.error(f"Error en process_pdfs: {str(e)}")
        raise