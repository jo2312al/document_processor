-- Esquema propuesto para administrar tipos documentales, campos y modelos NLP.
-- Pensado para MySQL 8+ y compatible con el enfoque actual del proyecto.

CREATE TABLE IF NOT EXISTS tipos_documento (
    id_tipo_documento INT AUTO_INCREMENT PRIMARY KEY,
    clave_tipo_documento VARCHAR(100) NOT NULL UNIQUE,
    nombre VARCHAR(150) NOT NULL,
    descripcion TEXT NULL,
    estado ENUM('borrador', 'activo', 'inactivo') NOT NULL DEFAULT 'borrador',
    paginas_esperadas INT NULL,
    origen_documento ENUM('escaneado', 'digital', 'escaneado_o_digital') NOT NULL DEFAULT 'escaneado_o_digital',
    fecha_creacion TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    fecha_actualizacion TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS campos_documento (
    id_campo_documento INT AUTO_INCREMENT PRIMARY KEY,
    id_tipo_documento INT NOT NULL,
    clave_campo VARCHAR(100) NOT NULL,
    nombre VARCHAR(150) NOT NULL,
    etiqueta_entidad VARCHAR(100) NOT NULL,
    descripcion TEXT NULL,
    obligatorio BOOLEAN NOT NULL DEFAULT FALSE,
    tipo_dato ENUM('texto', 'numero', 'fecha', 'correo', 'telefono', 'catalogo') NOT NULL DEFAULT 'texto',
    expresion_validacion VARCHAR(255) NULL,
    orden_visualizacion INT NOT NULL DEFAULT 0,
    fecha_creacion TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_campos_tipo_documento
        FOREIGN KEY (id_tipo_documento) REFERENCES tipos_documento(id_tipo_documento)
        ON DELETE CASCADE,
    CONSTRAINT uq_campo_por_tipo UNIQUE (id_tipo_documento, clave_campo),
    CONSTRAINT uq_entidad_por_tipo UNIQUE (id_tipo_documento, etiqueta_entidad)
);

CREATE TABLE IF NOT EXISTS rasgos_documento (
    id_rasgo_documento INT AUTO_INCREMENT PRIMARY KEY,
    id_tipo_documento INT NOT NULL,
    nombre_rasgo VARCHAR(100) NOT NULL,
    valor_rasgo VARCHAR(255) NOT NULL,
    peso DECIMAL(5,2) NOT NULL DEFAULT 1.00,
    CONSTRAINT fk_rasgos_tipo_documento
        FOREIGN KEY (id_tipo_documento) REFERENCES tipos_documento(id_tipo_documento)
        ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS versiones_modelo (
    id_version_modelo INT AUTO_INCREMENT PRIMARY KEY,
    id_tipo_documento INT NOT NULL,
    nombre_modelo VARCHAR(150) NOT NULL,
    ruta_modelo VARCHAR(255) NOT NULL,
    estado ENUM('entrenamiento', 'pruebas', 'activo', 'archivado') NOT NULL DEFAULT 'pruebas',
    documentos_entrenamiento INT NOT NULL DEFAULT 0,
    precision_entidades DECIMAL(6,4) NULL,
    recall_entidades DECIMAL(6,4) NULL,
    f1_entidades DECIMAL(6,4) NULL,
    observaciones TEXT NULL,
    fecha_entrenamiento TIMESTAMP NULL,
    fecha_registro TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_modelos_tipo_documento
        FOREIGN KEY (id_tipo_documento) REFERENCES tipos_documento(id_tipo_documento)
        ON DELETE CASCADE,
    CONSTRAINT uq_modelo_por_tipo UNIQUE (id_tipo_documento, nombre_modelo)
);

CREATE TABLE IF NOT EXISTS documentos_entrenamiento (
    id_documento_entrenamiento INT AUTO_INCREMENT PRIMARY KEY,
    id_tipo_documento INT NOT NULL,
    nombre_archivo VARCHAR(255) NOT NULL,
    ruta_archivo VARCHAR(255) NOT NULL,
    texto_ocr LONGTEXT NULL,
    estado ENUM('cargado', 'ocr_generado', 'anotado', 'validado', 'descartado') NOT NULL DEFAULT 'cargado',
    fecha_carga TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_documentos_tipo_documento
        FOREIGN KEY (id_tipo_documento) REFERENCES tipos_documento(id_tipo_documento)
        ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS anotaciones_entrenamiento (
    id_anotacion_entrenamiento INT AUTO_INCREMENT PRIMARY KEY,
    id_documento_entrenamiento INT NOT NULL,
    id_campo_documento INT NOT NULL,
    texto_anotado TEXT NOT NULL,
    posicion_inicio INT NOT NULL,
    posicion_fin INT NOT NULL,
    validado BOOLEAN NOT NULL DEFAULT FALSE,
    fecha_anotacion TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_anotaciones_documento
        FOREIGN KEY (id_documento_entrenamiento) REFERENCES documentos_entrenamiento(id_documento_entrenamiento)
        ON DELETE CASCADE,
    CONSTRAINT fk_anotaciones_campo
        FOREIGN KEY (id_campo_documento) REFERENCES campos_documento(id_campo_documento)
        ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS procesamientos_documento (
    id_procesamiento_documento INT AUTO_INCREMENT PRIMARY KEY,
    id_tipo_documento INT NOT NULL,
    id_version_modelo INT NULL,
    nombre_archivo VARCHAR(255) NOT NULL,
    estado ENUM('procesado', 'error') NOT NULL,
    campos_extraidos JSON NULL,
    campos_faltantes JSON NULL,
    mensaje_error TEXT NULL,
    tiempo_procesamiento_ms INT NULL,
    fecha_procesamiento TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_procesamientos_tipo_documento
        FOREIGN KEY (id_tipo_documento) REFERENCES tipos_documento(id_tipo_documento),
    CONSTRAINT fk_procesamientos_version_modelo
        FOREIGN KEY (id_version_modelo) REFERENCES versiones_modelo(id_version_modelo)
);
