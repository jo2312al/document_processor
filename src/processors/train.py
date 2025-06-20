import os
import sys
import json
import logging
import time
import torch
import psutil
from torch.utils.data import Dataset, DataLoader
from transformers import LayoutLMForTokenClassification, LayoutLMTokenizerFast
from sklearn.metrics import precision_recall_fscore_support
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))
from config import BASE_DIR, DATA_DIR, MODELS_DIR, LOGS_DIR, LOGGING_FORMAT, LOGGING_LEVEL

# Configurar logging
os.makedirs(LOGS_DIR, exist_ok=True)
logging.basicConfig(
    filename=os.path.join(LOGS_DIR, "training.log"),
    level=getattr(logging, LOGGING_LEVEL),
    format=LOGGING_FORMAT
)
logger = logging.getLogger(__name__)

def log_resources(start_time, epoch=None):
    """Registra uso de CPU, RAM y GPU (si aplica)."""
    cpu_usage = psutil.cpu_percent(interval=0.1)
    memory_info = psutil.virtual_memory()
    ram_usage_mb = memory_info.used / (1024 ** 2)
    gpu_usage = "N/A"
    gpu_memory = "N/A"
    if torch.cuda.is_available():
        try:
            gpu_memory_allocated = torch.cuda.memory_allocated() / (1024 ** 2)
            gpu_memory_cached = torch.cuda.memory_reserved() / (1024 ** 2)
            gpu_memory = f"{gpu_memory_allocated:.2f}/{gpu_memory_cached:.2f} MB"
        except Exception as e:
            gpu_memory = f"Error: {str(e)}"
    elapsed_time = time.time() - start_time
    log_msg = (
        f"{'Epoch ' + str(epoch+1) if epoch is not None else 'Total'} - "
        f"CPU: {cpu_usage:.1f}%, RAM: {ram_usage_mb:.2f} MB, GPU: {gpu_usage}, "
        f"GPU Memory: {gpu_memory}, Time: {elapsed_time:.2f}s"
    )
    logger.info(log_msg)
    print(log_msg)
    return elapsed_time

class PDFDataset(Dataset):
    def __init__(self, annotations_file, tokenizer, max_length=512):
        self.tokenizer = tokenizer
        self.max_length = max_length
        with open(annotations_file, 'r', encoding='utf-8') as f:
            self.data = json.load(f)
        self.labels_map = {
            "O": 0,
            "B-ALU_MATRICULA": 1, "I-ALU_MATRICULA": 2,
            "B-ALU_NOMBRE": 3, "I-ALU_NOMBRE": 4,
            "B-ALU_PATERNO": 5, "I-ALU_PATERNO": 6,
            "B-ALU_MATERNO": 7, "I-ALU_MATERNO": 8,
            "B-ALU_CARRERA": 9, "I-ALU_CARRERA": 10,
            "B-ALU_SERVICIO": 11, "I-ALU_SERVICIO": 12
        }
        logger.info(f"Cargados {len(self.data)} ejemplos desde {annotations_file}")

    def __len__(self):
        return len(self.data)

    def __getitem__(self, idx):
        item = self.data[idx]
        tokens = item["tokens"]
        bboxes = item["bboxes"]
        labels = item["labels"]

        # Validar y corregir bboxes
        bboxes = [
            [0, 0, 1000, 1000] if not bbox or bbox == [0, 0, 0, 0] or 
            (bbox[2] - bbox[0] <= 10 or bbox[3] - bbox[1] <= 10) else bbox 
            for bbox in bboxes
        ]

        # Tokenizar sin bboxes
        encoding = self.tokenizer(
            tokens,
            is_split_into_words=True,
            return_tensors="pt",
            truncation=True,
            padding="max_length",
            max_length=self.max_length,
            return_offsets_mapping=True
        )

        # Alinear etiquetas y bboxes con subwords
        word_ids = encoding.word_ids()
        aligned_labels = [-100] * self.max_length
        aligned_bboxes = [[0, 0, 1000, 1000]] * self.max_length

        for i, word_id in enumerate(word_ids):
            if word_id is None:
                continue
            if word_id < len(labels):
                aligned_labels[i] = self.labels_map.get(labels[word_id], 0)
                aligned_bboxes[i] = bboxes[word_id] if word_id < len(bboxes) else [0, 0, 1000, 1000]

        return {
            "input_ids": encoding["input_ids"].squeeze(),
            "attention_mask": encoding["attention_mask"].squeeze(),
            "bbox": torch.tensor(aligned_bboxes, dtype=torch.long),
            "labels": torch.tensor(aligned_labels, dtype=torch.long)
        }

def train_model():
    logger.info("Iniciando entrenamiento de LayoutLM")
    start_time = time.time()
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    logger.info(f"Usando dispositivo: {device}")

    tokenizer = LayoutLMTokenizerFast.from_pretrained("microsoft/layoutlm-base-uncased")
    model = LayoutLMForTokenClassification.from_pretrained(
        "microsoft/layoutlm-base-uncased",
        num_labels=13
    ).to(device)

    annotations_file = os.path.join(DATA_DIR, "annotations.json")
    dataset = PDFDataset(annotations_file, tokenizer)
    
    train_size = int(0.8 * len(dataset))
    val_size = len(dataset) - train_size
    train_dataset, val_dataset = torch.utils.data.random_split(dataset, [train_size, val_size])

    train_loader = DataLoader(train_dataset, batch_size=4, shuffle=True)
    val_loader = DataLoader(val_dataset, batch_size=4)

    optimizer = torch.optim.AdamW(model.parameters(), lr=2e-5)
    num_epochs = 3

    for epoch in range(num_epochs):
        epoch_start_time = time.time()
        model.train()
        train_loss = 0
        for batch in train_loader:
            input_ids = batch["input_ids"].to(device)
            attention_mask = batch["attention_mask"].to(device)
            bbox = batch["bbox"].to(device)
            labels = batch["labels"].to(device)

            outputs = model(
                input_ids=input_ids,
                attention_mask=attention_mask,
                bbox=bbox,
                labels=labels
            )
            loss = outputs.loss
            train_loss += loss.item()

            optimizer.zero_grad()
            loss.backward()
            optimizer.step()

        avg_train_loss = train_loss / len(train_loader)
        logger.info(f"Epoch {epoch+1}/{num_epochs}, Train Loss: {avg_train_loss:.4f}")

        model.eval()
        val_loss = 0
        all_preds = []
        all_labels = []
        with torch.no_grad():
            for batch in val_loader:
                input_ids = batch["input_ids"].to(device)
                attention_mask = batch["attention_mask"].to(device)
                bbox = batch["bbox"].to(device)
                labels = batch["labels"].to(device)

                outputs = model(
                    input_ids=input_ids,
                    attention_mask=attention_mask,
                    bbox=bbox,
                    labels=labels
                )
                val_loss += outputs.loss.item()

                preds = torch.argmax(outputs.logits, dim=2).cpu().numpy()
                labels = labels.cpu().numpy()
                for p, l in zip(preds, labels):
                    valid_indices = l != -100
                    all_preds.extend(p[valid_indices])
                    all_labels.extend(l[valid_indices])

        avg_val_loss = val_loss / len(val_loader)
        precision, recall, f1, _ = precision_recall_fscore_support(
            all_labels, all_preds, average='weighted', zero_division=1
        )
        logger.info(f"Epoch {epoch+1}/{num_epochs}, Val Loss: {avg_val_loss:.4f}, Precision: {precision:.4f}, Recall: {recall:.4f}, F1: {f1:.4f}")
        log_resources(epoch_start_time, epoch)

    model.save_pretrained(os.path.join(MODELS_DIR, "layoutlm_model"))
    tokenizer.save_pretrained(os.path.join(MODELS_DIR, "layoutlm_model"))
    logger.info("Modelo guardado en models/layoutlm_model")
    total_time = log_resources(start_time)
    return total_time

if __name__ == "__main__":
    try:
        train_model()
    except Exception as e:
        logger.error(f"Error en entrenamiento: {str(e)}")
        raise