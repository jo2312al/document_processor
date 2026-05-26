import os
import platform


IS_WINDOWS = platform.system() == "Windows"

BASE_DIR = os.getenv(
    "DOCUMENT_PROCESSOR_BASE_DIR",
    r"C:\python\document_processor" if IS_WINDOWS else os.path.dirname(os.path.abspath(__file__)),
)

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

TESSERACT_CMD = os.getenv(
    "TESSERACT_CMD",
    r"C:\Program Files\Tesseract-OCR\tesseract.exe" if IS_WINDOWS else "/usr/bin/tesseract",
)
POPPLER_PATH = os.getenv(
    "POPPLER_PATH",
    r"C:\Program Files\Poppler\Library\bin" if IS_WINDOWS else "/usr/bin",
)

LOGGING_FORMAT = "%(asctime)s - %(levelname)s - %(message)s"
LOGGING_LEVEL = os.getenv("LOGGING_LEVEL", "INFO")

for directory in [LOGS_DIR, UPLOADS_DIR]:
    os.makedirs(directory, exist_ok=True)
