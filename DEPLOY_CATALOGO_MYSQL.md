# Catalogo documental con MySQL

El sistema puede trabajar con dos fuentes para tipos documentales, campos y versiones de modelo:

- `json`: modo predeterminado para desarrollo local.
- `mysql`: modo recomendado para despliegue y uso administrativo.

## Activar MySQL

1. Ejecutar el esquema:

```bash
mysql -u pipeline -p servicio < database/schema_documentos.sql
```

2. Configurar variables de entorno en la VM o en el servicio systemd:

```bash
export CATALOGO_DOCUMENTAL_BACKEND=mysql
export MYSQL_HOST=localhost
export MYSQL_USER=pipeline
export MYSQL_PASSWORD=pipeline2312
export MYSQL_DATABASE=servicio
export MYSQL_PORT=3306
export TIPO_DOCUMENTO_PREDETERMINADO=constancia_servicio
export ADMIN_API_TOKEN=coloca_un_token_largo
```

3. Reiniciar la API:

```bash
sudo systemctl restart document-processor
```

## Endpoints administrativos

Todos los endpoints administrativos requieren el header:

```text
X-Admin-Token: coloca_un_token_largo
```

Crear tipo documental:

```http
POST /admin/tipos-documento
```

Agregar campo:

```http
POST /admin/tipos-documento/{id_tipo_documento}/campos
```

Registrar version de modelo:

```http
POST /admin/tipos-documento/{id_tipo_documento}/modelos
```

## Nota tecnica

El modo JSON permite seguir desarrollando sin MySQL instalado. El modo MySQL usa las mismas funciones del gestor, por lo que la API no necesita cambiar cuando se migra la persistencia.
