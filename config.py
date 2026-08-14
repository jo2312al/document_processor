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
DOCUMENTOS_ENTRENAMIENTO_DIR = os.path.join(DATA_DIR, "documentos_entrenamiento")
DOCUMENTOS_VALIDADOS_DIR = os.path.join(DATA_DIR, "documentos_validados")
FONTS_DIR = os.path.join(BASE_DIR, "fonts")
CONFIG_DIR = os.path.join(BASE_DIR, "src", "configuracion")
TIPOS_DOCUMENTO_PATH = os.getenv("TIPOS_DOCUMENTO_PATH", os.path.join(CONFIG_DIR, "tipos_documento.json"))
API_KEYS_PATH = os.getenv("API_KEYS_PATH", os.path.join(CONFIG_DIR, "api_keys.json"))
APRENDIZAJE_ACTIVO_PATH = os.getenv("APRENDIZAJE_ACTIVO_PATH", os.path.join(DATA_DIR, "aprendizaje_activo.json"))
APRENDIZAJE_LOTES_PATH = os.getenv("APRENDIZAJE_LOTES_PATH", os.path.join(DATA_DIR, "lotes_aprendizaje.json"))
PREPROCESADOR_DOCUMENTAL = os.getenv("PREPROCESADOR_DOCUMENTAL", "tesseract").lower()

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
ADMIN_API_TOKEN = os.getenv("ADMIN_API_TOKEN")
ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "admin")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD") or ADMIN_API_TOKEN
SESSION_SECRET_KEY = os.getenv("SESSION_SECRET_KEY") or ADMIN_API_TOKEN or "document-processor-dev"
CATALOGO_DOCUMENTAL_BACKEND = os.getenv("CATALOGO_DOCUMENTAL_BACKEND", "json").lower()
TIPO_DOCUMENTO_PREDETERMINADO = os.getenv("TIPO_DOCUMENTO_PREDETERMINADO", "constancia_servicio")
UMBRAL_LOTE_ENTRENAMIENTO = int(os.getenv("UMBRAL_LOTE_ENTRENAMIENTO", "50"))
EPOCAS_ENTRENAMIENTO_LOTE = int(os.getenv("EPOCAS_ENTRENAMIENTO_LOTE", "8"))

CELERY_BROKER_URL = os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/0")
CELERY_RESULT_BACKEND = os.getenv("CELERY_RESULT_BACKEND", "redis://localhost:6379/1")
CELERY_TASK_ALWAYS_EAGER = os.getenv("CELERY_TASK_ALWAYS_EAGER", "0") == "1"

MYSQL_HOST = os.getenv("MYSQL_HOST", "localhost")
MYSQL_USER = os.getenv("MYSQL_USER", "root")
MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD", "2312")
MYSQL_DATABASE = os.getenv("MYSQL_DATABASE", "servicio")
MYSQL_PORT = int(os.getenv("MYSQL_PORT", "3306"))

for directory in [LOGS_DIR, UPLOADS_DIR, DOCUMENTOS_ENTRENAMIENTO_DIR, DOCUMENTOS_VALIDADOS_DIR]:
    os.makedirs(directory, exist_ok=True)
