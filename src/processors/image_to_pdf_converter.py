import os
from PIL import Image
import logging
import sys
import argparse
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))
from config import BASE_DIR, LOGS_DIR, LOGGING_FORMAT, LOGGING_LEVEL

# Configurar rutas
IMAGE_DIR = os.path.join(BASE_DIR, 'generated_images')
OUTPUT_DIR = os.path.join(BASE_DIR, 'converted_pdfs')
LOG_FILE = os.path.join(LOGS_DIR, 'image_to_pdf_converter.log')

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
logger.info("Logging configurado correctamente")

def convert_images_to_pdf(num_images=None):
    """Convierte imágenes JPG a PDFs, procesando todas las imágenes disponibles."""
    logger.info("Iniciando conversión de imágenes a PDFs")
    print("Iniciando conversión de imágenes a PDFs")
    
    image_files = [f for f in os.listdir(IMAGE_DIR) if f.endswith('.jpg')]
    total_images = len(image_files)
    logger.info(f"Encontradas {total_images} imágenes en {IMAGE_DIR}: {image_files[:5]}...")
    print(f"Encontradas {total_images} imágenes")
    
    if not image_files:
        logger.warning(f"No se encontraron imágenes en {IMAGE_DIR}")
        print(f"Advertencia: No se encontraron imágenes en {IMAGE_DIR}")
        return

    # Validar num_images
    if num_images is not None and num_images > 0:
        if num_images > total_images:
            logger.warning(f"Solicitadas {num_images} imágenes, pero solo hay {total_images}. Procesando todas.")
            print(f"Advertencia: Solicitadas {num_images} imágenes, pero solo hay {total_images}. Procesando todas.")
        elif num_images < total_images:
            logger.info(f"Solicitadas {num_images} imágenes de {total_images}. Procesando {num_images}.")
            print(f"Solicitadas {num_images} imágenes de {total_images}. Procesando {num_images}.")
            image_files = sorted(image_files)[:num_images]  # Procesar en orden alfabético
        else:
            logger.info(f"Procesando todas las {total_images} imágenes (num_images={num_images})")
            print(f"Procesando todas las {total_images} imágenes")
    else:
        logger.info(f"Procesando todas las {total_images} imágenes (num_images no especificado)")
        print(f"Procesando todas las {total_images} imágenes")

    processed_count = 0
    for image_file in image_files:
        try:
            image_path = os.path.join(IMAGE_DIR, image_file)
            pdf_path = os.path.join(OUTPUT_DIR, f"{os.path.splitext(image_file)[0]}.pdf")
            
            with Image.open(image_path) as img:
                img.save(pdf_path, "PDF", resolution=100.0)
            logger.info(f"Convertida {image_file} a {pdf_path}")
            print(f"Convertida {image_file} a {pdf_path}")
            processed_count += 1
        
        except Exception as e:
            logger.error(f"Error procesando {image_file}: {str(e)}")
            print(f"Error procesando {image_file}: {str(e)}")
            continue

    logger.info(f"Conversión finalizada: {processed_count}/{total_images} imágenes procesadas")
    print(f"Conversión finalizada: {processed_count}/{total_images} imágenes procesadas")
    
    # Validar que se procesaron todas las imágenes esperadas
    expected_images = num_images if num_images is not None and num_images <= total_images else total_images
    if processed_count < expected_images:
        logger.error(f"No se procesaron todas las imágenes esperadas: {processed_count}/{expected_images}")
        print(f"Error: No se procesaron todas las imágenes esperadas: {processed_count}/{expected_images}")
        raise RuntimeError(f"No se procesaron todas las imágenes esperadas: {processed_count}/{expected_images}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Convierte imágenes a PDFs.")
    parser.add_argument("--num_images", type=int, default=None, help="Número de imágenes a procesar (procesa todas si no se especifica o si es mayor al total)")
    args = parser.parse_args()
    
    try:
        convert_images_to_pdf(num_images=args.num_images)
    except KeyboardInterrupt:
        logger.info("Interrupción por teclado, finalizando ejecución")
        print("Interrupción por teclado, finalizando ejecución")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Error en la ejecución principal: {str(e)}")
        print(f"Error en la ejecución principal: {str(e)}")
        sys.exit(1)