import os
import json
import logging
import sys
import argparse
import random
import spacy
from spacy.training.example import Example
from spacy.util import minibatch, compounding
from tqdm import tqdm

# --- Configuración de rutas ---
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))
from config import DATA_DIR, MODELS_DIR

# --- Función Principal (Lógica Encapsulada) ---
def run_training(model_path=None, n_iter=30, dropout=0.35, batch_size=8):
    """
    Entrena o re-entrena un modelo NER de spaCy.
    """
    logger = logging.getLogger("pipeline_integrado.train_spacy")
    training_data_file = os.path.join(DATA_DIR, 'spacy_training_data.json')
    output_model_dir = os.path.join(MODELS_DIR, 'spacy_model')

    # Cargar modelo existente o crear uno nuevo
    if model_path and os.path.exists(model_path):
        nlp = spacy.load(model_path)
        logger.info(f"Modelo cargado desde '{model_path}' para re-entrenamiento.")
        print(f"\nModelo cargado desde '{model_path}' para continuar entrenamiento.")
    else:
        nlp = spacy.blank("es")
        logger.info("Creado modelo 'es' en blanco para entrenamiento desde cero.")
        print("\nCreando modelo nuevo desde cero.")

    # Cargar datos de entrenamiento
    if not os.path.exists(training_data_file):
        logger.error(f"No se encontró el archivo de datos: {training_data_file}")
        raise FileNotFoundError(f"Archivo no encontrado: {training_data_file}")
    
    with open(training_data_file, 'r', encoding='utf-8') as f:
        TRAIN_DATA = json.load(f)
    logger.info(f"Cargados {len(TRAIN_DATA)} ejemplos de entrenamiento.")

    # Configurar el pipeline de NER
    if "ner" not in nlp.pipe_names:
        ner = nlp.add_pipe("ner", last=True)
    else:
        ner = nlp.get_pipe("ner")

    for _, annotations in TRAIN_DATA:
        for ent in annotations.get("entities"):
            ner.add_label(ent[2])

    # Bucle de entrenamiento
    other_pipes = [pipe for pipe in nlp.pipe_names if pipe != "ner"]
    with nlp.disable_pipes(*other_pipes):
        optimizer = nlp.resume_training() if model_path and os.path.exists(model_path) else nlp.begin_training()
        
        for itn in range(n_iter):
            random.shuffle(TRAIN_DATA)
            losses = {}
            # Usar tqdm para la barra de progreso de los lotes
            batches = minibatch(TRAIN_DATA, size=compounding(4.0, batch_size, 1.001))
            
            with tqdm(total=len(TRAIN_DATA), desc=f"Iteración {itn + 1}/{n_iter}") as pbar:
                for batch in batches:
                    examples = []
                    for text, annotations in batch:
                        try:
                            doc = nlp.make_doc(text)
                            examples.append(Example.from_dict(doc, annotations))
                        except ValueError as e:
                            # Ignorar errores de alineación que puedan surgir
                            logger.warning(f"Saltando ejemplo por error de alineación: {e}")
                            continue
                    
                    if examples: # Solo actualizar si hay ejemplos válidos
                        nlp.update(examples, drop=dropout, sgd=optimizer, losses=losses)
                    
                    pbar.update(len(batch))
                    pbar.set_postfix(loss=f"{losses.get('ner', 0.0):.2f}")

            logger.info(f"Iteración {itn + 1}/{n_iter}, Pérdida (Loss): {losses.get('ner', 0.0):.4f}")

    # Guardar el modelo final
    if not os.path.exists(output_model_dir):
        os.makedirs(output_model_dir)
    nlp.to_disk(output_model_dir)
    logger.info(f"Modelo final guardado en: {output_model_dir}")
    print(f"\n¡Entrenamiento completado! Modelo guardado en: {output_model_dir}")

# --- Bloque de Ejecución Independiente ---
if __name__ == "__main__":
    from config import LOGS_DIR, LOGGING_FORMAT, LOGGING_LEVEL
    
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    
    parser = argparse.ArgumentParser(description="Entrena o re-entrena un modelo NER de spaCy.")
    parser.add_argument("--iter", type=int, default=30, help="Número de iteraciones de entrenamiento.")
    parser.add_argument("--model_path", type=str, default=None, help="Ruta a un modelo existente para continuar el entrenamiento (opcional).")
    args = parser.parse_args()
    
    model_path_arg = args.model_path if args.model_path else os.path.join(MODELS_DIR, 'spacy_model')
    
    print(f"Iniciando entrenamiento...")
    try:
        run_training(model_path=model_path_arg, n_iter=args.iter)
    except Exception as e:
        logging.error(f"Error fatal en la ejecución independiente: {e}", exc_info=True)
        print(f"ERROR: {e}")
