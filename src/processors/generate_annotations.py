import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))
import json
import cv2
import logging
from config import LABELS_DIR, YOLO_DIR, DATA_DIR, GENERATED_IMAGES_DIR, LOGS_DIR, LOGGING_FORMAT, LOGGING_LEVEL

# Configurar logging
os.makedirs(LOGS_DIR, exist_ok=True)
logging.basicConfig(
    filename=os.path.join(LOGS_DIR, 'generate_annotations.log'),
    level=getattr(logging, LOGGING_LEVEL),
    format=LOGGING_FORMAT
)
logger = logging.getLogger(__name__)

def normalize_bbox(bbox, img_width, img_height):
    """Normaliza bbox [x, y, w, h] a [x_min, y_min, x_max, y_max] entre 0 y 1000."""
    x, y, w, h = bbox
    if w <= 0 or h <= 0:
        return [0, 0, 1000, 1000]
    x_min = max(0, x) / img_width * 1000
    y_min = max(0, y) / img_height * 1000
    x_max = min(x + w, img_width) / img_width * 1000
    y_max = min(y + h, img_height) / img_height * 1000
    return [int(x_min), int(y_min), int(x_max), int(y_max)]

def get_image_dimensions(json_path):
    """Obtiene dimensiones desde JSON o usa valores predeterminados."""
    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        dims = data.get('image_dimensions', {})
        if 'width' in dims and 'height' in dims:
            return dims['width'], dims['height']
        logger.warning(f"No se encontraron dimensiones en {json_path}, usando default")
        return 595, 842
    except Exception as e:
        logger.error(f"Error al leer dimensiones de {json_path}: {str(e)}")
        return 595, 842

def generate_annotations():
    """Genera annotations.json con bboxes normalizadas."""
    logger.info("Iniciando generación de annotations.json")
    annotations = []
    json_files = [f for f in os.listdir(LABELS_DIR) if f.endswith('.json') and f.startswith('labels_constancia')]
    
    class_map = {
        0: 'B-ALU_MATRICULA', 1: 'B-ALU_NOMBRE', 2: 'B-ALU_PATERNO',
        3: 'B-ALU_MATERNO', 4: 'B-ALU_CARRERA', 5: 'B-ALU_SERVICIO'
    }
    field_order = ['alu_matricula', 'alu_nombre', 'alu_paterno', 'alu_materno', 'alu_carrera', 'alu_servicio']

    for json_file in json_files:
        try:
            base_name = json_file.replace('labels_', '').replace('.json', '')
            yolo_file = f"{base_name}_page_1.txt"
            yolo_path = os.path.join(YOLO_DIR, yolo_file)
            json_path = os.path.join(LABELS_DIR, json_file)

            # Obtener dimensiones desde JSON
            img_width, img_height = get_image_dimensions(json_path)
            logger.info(f"Dimensiones para {json_file}: {img_width}x{img_height}")

            # Cargar JSON
            with open(json_path, 'r', encoding='utf-8') as f:
                label_data = json.load(f)
            
            tokens = []
            bboxes = []
            labels = []
            fields = label_data.get('fields', {})

            # Procesar campos en orden
            for field_name in field_order:
                field_data = fields.get(field_name, {})
                value = field_data.get('value', '').strip()
                tokens.append(value)
                labels.append(f"B-{field_name.upper()}")
                
                # Buscar bbox en YOLO
                found = False
                if os.path.exists(yolo_path):
                    with open(yolo_path, 'r') as f:
                        yolo_lines = f.readlines()
                    
                    class_id = list(class_map.keys())[list(class_map.values()).index(f'B-{field_name.upper()}')]
                    for line in yolo_lines:
                        parts = line.strip().split()
                        if len(parts) == 5 and int(parts[0]) == class_id:
                            x_center, y_center, w_norm, h_norm = map(float, parts[1:])
                            x = (x_center - w_norm / 2) * img_width
                            y = (y_center - h_norm / 2) * img_height
                            w = w_norm * img_width
                            h = h_norm * img_height
                            if w > 5 and h > 5:
                                bbox = normalize_bbox([x, y, w, h], img_width, img_height)
                                bboxes.append(bbox)
                                found = True
                                logger.info(f"Bbox válida para {field_name} en {yolo_file}: {bbox}")
                                break
                
                if not found:
                    logger.warning(f"No se encontró bbox válida para {field_name} en {yolo_file}, usando default")
                    bboxes.append([0, 0, 1000, 1000])

            annotations.append({
                "filename": f"{base_name}_page_1.pdf",
                "tokens": tokens,
                "bboxes": bboxes,
                "labels": labels
            })
        
        except Exception as e:
            logger.error(f"Error procesando {json_file}: {str(e)}")
            continue
    
    output_path = os.path.join(DATA_DIR, 'annotations.json')
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(annotations, f, ensure_ascii=False, indent=2)
    logger.info(f"Generado {output_path} con {len(annotations)} entradas")
    print(f"Generado {output_path} con {len(annotations)} entradas")

if __name__ == "__main__":
    try:
        generate_annotations()
    except Exception as e:
        logger.error(f"Error en la ejecución principal: {str(e)}")
        print(f"Error en la ejecución principal: {str(e)}")