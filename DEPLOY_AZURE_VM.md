# Deploy en Azure VM Ubuntu

Guia para desplegar la API Flask del procesador de documentos en una VM Ubuntu.

## 1. Preparar la VM

Conectarse por SSH:

```bash
ssh <usuario>@<IP_PUBLICA>
```

Instalar dependencias del sistema:

```bash
sudo apt update
sudo apt upgrade -y
sudo apt install -y python3 python3-venv python3-pip git nginx tesseract-ocr tesseract-ocr-spa poppler-utils
```

Verificar herramientas:

```bash
python3 --version
tesseract --version
pdftoppm -v
nginx -v
```

## 2. Clonar el proyecto

```bash
cd /home/<usuario>
git clone https://github.com/jo2312al/document_processor.git
cd document_processor
```

## 3. Crear entorno Python

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements-deploy.txt
```

## 4. Crear carpetas locales

```bash
mkdir -p logs uploads models
```

## 5. Copiar el modelo spaCy

El modelo `models/spacy_model` no debe ir en Git si pesa mucho o se considera artefacto local. Copiarlo desde Windows con `scp`:

```powershell
scp -r C:\python\document_processor\models\spacy_model <usuario>@<IP_PUBLICA>:/home/<usuario>/document_processor/models/
```

En la VM, verificar:

```bash
ls -la models/spacy_model
```

## 6. Probar la API con Gunicorn

```bash
source .venv/bin/activate
gunicorn -w 2 -b 127.0.0.1:5000 api:app
```

En otra terminal:

```bash
curl http://127.0.0.1:5000/
```

## 7. Crear servicio systemd

Crear archivo:

```bash
sudo nano /etc/systemd/system/document-processor.service
```

Contenido:

```ini
[Unit]
Description=Document Processor Flask API
After=network.target

[Service]
User=<usuario>
Group=www-data
WorkingDirectory=/home/<usuario>/document_processor
Environment="DOCUMENT_PROCESSOR_BASE_DIR=/home/<usuario>/document_processor"
Environment="TESSERACT_CMD=/usr/bin/tesseract"
Environment="POPPLER_PATH=/usr/bin"
ExecStart=/home/<usuario>/document_processor/.venv/bin/gunicorn -w 2 -b 127.0.0.1:5000 api:app
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

Activar:

```bash
sudo systemctl daemon-reload
sudo systemctl enable document-processor
sudo systemctl start document-processor
sudo systemctl status document-processor
```

## 8. Configurar Nginx

Crear archivo:

```bash
sudo nano /etc/nginx/sites-available/document-processor
```

Contenido:

```nginx
server {
    listen 80;
    server_name _;

    client_max_body_size 16M;

    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

Activar sitio:

```bash
sudo ln -s /etc/nginx/sites-available/document-processor /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

Abrir en navegador:

```text
http://<IP_PUBLICA>
```

## 9. Logs utiles

```bash
sudo journalctl -u document-processor -f
tail -f logs/api.log
```

## 10. Actualizar codigo en la VM

```bash
cd /home/<usuario>/document_processor
git pull
source .venv/bin/activate
pip install -r requirements-deploy.txt
sudo systemctl restart document-processor
```

## 11. Deploy automatico con GitHub Actions

El workflow `.github/workflows/deploy-azure-vm.yml` despliega automaticamente cuando se hace push a `main`.

Configurar estos secretos en GitHub:

```text
AZURE_VM_HOST=52.186.173.159
AZURE_VM_USER=azureuser
AZURE_VM_SSH_KEY=<contenido completo de machine_key.pem>
```

Ruta en GitHub:

```text
Settings -> Secrets and variables -> Actions -> New repository secret
```

Para obtener el contenido de la llave en Windows:

```powershell
Get-Content C:\Users\jomej\Downloads\machine_key.pem -Raw
```

El deploy automatico hace:

```bash
cd /home/$USER/document_processor
git pull --ff-only origin main
source .venv/bin/activate
pip install -r requirements-deploy.txt
sudo systemctl restart document-processor
```
