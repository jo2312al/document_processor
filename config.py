import os
import platform

# Detectar sistema operativo
IS_WINDOWS = platform.system() == "Windows"

# Rutas base
BASE_DIR = r"C:\python\document_processor" if IS_WINDOWS else "/home/user/document_processor"
DATA_DIR = os.path.join(BASE_DIR, "data")
GENERATED_DOCS_DIR = os.path.join(BASE_DIR, "generated_docs")
GENERATED_IMAGES_DIR = os.path.join(BASE_DIR, "generated_images")
CONVERTED_PDFS_DIR = os.path.join(BASE_DIR, "converted_pdfs")
GENERATED_PDFS_FROM_IMAGES_DIR = os.path.join(BASE_DIR, "generated_pdfs_from_images")
LABELS_DIR = os.path.join(BASE_DIR, "labels")
YOLO_DIR = os.path.join(LABELS_DIR, "yolo")
LOGS_DIR = os.path.join(BASE_DIR, "logs")
DATASET_DIR = os.path.join(BASE_DIR, "dataset")
MODELS_DIR = os.path.join(BASE_DIR, "models")
UPLOADS_DIR = os.path.join(BASE_DIR, "uploads")
FONTS_DIR = os.path.join(BASE_DIR, "fonts")

# Rutas de herramientas
TESSERACT_CMD = r"C:\Program Files\Tesseract-OCR\tesseract.exe" if IS_WINDOWS else "/usr/bin/tesseract"
POPPLER_PATH = r"C:\Program Files\Poppler\Library\bin" if IS_WINDOWS else "/usr/bin"

# Configuración de logging
LOGGING_FORMAT = "%(asctime)s - %(levelname)s - %(message)s"
LOGGING_LEVEL = "INFO"