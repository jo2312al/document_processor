const estadoGlobal = document.getElementById('estado-global');
let tiposDocumento = [];
let tipoSeleccionado = null;
let documentoEntrenamientoSeleccionado = null;
let rangoSeleccionado = null;
let ultimaApiKey = 'TU_API_KEY';
let pasoTipo = 0;

iniciarPanel();

function iniciarPanel() {    conectarEventos();
    cargarTodo().catch(error => mostrarEstado(error.message, 'error'));
}

function conectarEventos() {    document.querySelectorAll('.tab').forEach(tab => tab.onclick = () => activarTab(tab.dataset.tab));
    document.getElementById('refrescar-lotes').onclick = cargarLotes;
    document.getElementById('abrir-wizard-tipo').onclick = abrirWizardTipo;
    document.getElementById('cerrar-wizard-tipo').onclick = cerrarWizardTipo;
    document.querySelectorAll('[data-next-tipo]').forEach(boton => boton.onclick = () => moverWizardTipo(1));
    document.querySelectorAll('[data-prev-tipo]').forEach(boton => boton.onclick = () => moverWizardTipo(-1));
    document.getElementById('form-tipo').onsubmit = crearTipoDesdeWizard;
    document.getElementById('form-plantilla').onsubmit = enviarPlantilla;
    document.getElementById('form-api-key').onsubmit = crearApiKey;
    document.getElementById('form-campo').onsubmit = crearCampo;
    document.getElementById('form-modelo').onsubmit = registrarModelo;
    document.getElementById('form-entrenamiento').onsubmit = subirDocumentoEntrenamiento;
    document.getElementById('texto-ocr-entrenamiento').onmouseup = capturarSeleccionOcr;
    document.getElementById('guardar-anotacion').onclick = guardarAnotacion;
}


function mostrarEstado(mensaje, clase = '') {
    estadoGlobal.textContent = mensaje;
    estadoGlobal.className = `estado ${clase}`;
}


function activarTab(tabId) {
    document.querySelectorAll('.tab').forEach(tab => tab.classList.toggle('activo', tab.dataset.tab === tabId));
    document.querySelectorAll('.tab-panel').forEach(panel => panel.classList.toggle('activo', panel.id === `tab-${tabId}`));
    if (tabId === 'aprendizaje') cargarLotes();
    if (tabId === 'api') cargarApiKeys();
}

async function apiJson(url, opciones = {}) {
    const headers = opciones.headers || {};
    if (opciones.body) headers['Content-Type'] = 'application/json';    const respuesta = await fetch(url, {...opciones, headers});
    const data = await respuesta.json();
    if (!respuesta.ok) throw new Error(data.error || 'Operacion no completada');
    return data;
}

async function cargarTodo() {
    await cargarTipos();
    await cargarDocumentosEntrenamiento();
    await cargarLotes();
    await cargarApiKeys();
}

async function cargarTipos() {
    const data = await apiJson('/tipos-documento');
    tiposDocumento = data.tipos_documento || [];
    if (!tipoSeleccionado && tiposDocumento.length) tipoSeleccionado = tiposDocumento[0].id_tipo_documento;
    renderTipos();
    renderDetalle();
    actualizarEjemplosApi();
}

function renderTipos() {
    const lista = document.getElementById('lista-tipos');
    lista.innerHTML = '';
    tiposDocumento.forEach(tipo => lista.appendChild(crearCardTipo(tipo)));
    if (!tiposDocumento.length) lista.innerHTML = '<div class="vacio">Sin tipos documentales.</div>';
}

function crearCardTipo(tipo) {
    const card = document.createElement('div');
    card.className = `tipo tipo-card ${tipo.id_tipo_documento === tipoSeleccionado ? 'activo' : ''}`;
    card.innerHTML = htmlTipoDocumento(tipo);
    card.querySelectorAll('[data-accion]').forEach(boton => configurarAccionTipo(boton, tipo));
    return card;
}

function configurarAccionTipo(boton, tipo) {
    boton.onclick = () => seleccionarTipo(tipo.id_tipo_documento, boton.dataset.accion);
}

function htmlTipoDocumento(tipo) {
    const plantilla = tipo.tiene_plantilla_activa ? 'Plantilla activa' : 'Sin plantilla';
    return `<div class="fila-titulo"><div><strong>${tipo.nombre}</strong><p class="muted">${tipo.id_tipo_documento}</p></div><span class="badge ${tipo.estado === 'activo' ? 'ok' : 'warn'}">${tipo.estado}</span></div><p class="muted">${tipo.descripcion || 'Sin descripcion registrada.'}</p><p class="muted">Modelo: ${tipo.modelo_activo || 'sin modelo'} - ${plantilla}</p><div class="tipo-acciones"><button class="fantasma" type="button" data-accion="documento">Ver</button><button class="fantasma" type="button" data-accion="campos">Campos</button><button class="fantasma" type="button" data-accion="plantilla">Plantilla</button><button class="fantasma" type="button" data-accion="entrenamiento">Anotar</button><button class="fantasma" type="button" data-accion="aprendizaje">Aprendizaje</button><button class="fantasma" type="button" data-accion="modelo">Modelos</button></div>`;
}

async function seleccionarTipo(idTipo, tabDestino = 'documento') {
    tipoSeleccionado = idTipo;
    renderTipos();
    renderDetalle();
    activarTab(tabDestino);
    await cargarDocumentosEntrenamiento();
    await cargarLotes();
}

function renderDetalle() {
    const tipo = tiposDocumento.find(item => item.id_tipo_documento === tipoSeleccionado);
    if (!tipo) return;
    document.getElementById('detalle-titulo').textContent = tipo.nombre;
    document.getElementById('detalle-descripcion').textContent = tipo.descripcion || 'Sin descripcion registrada.';
    document.getElementById('detalle-estado').textContent = `Estado: ${tipo.estado}`;
    document.getElementById('detalle-modelo').textContent = `Modelo: ${tipo.modelo_activo || 'sin modelo'}`;
    renderCampos(tipo.campos || []);
    renderModelos(tipo.versiones_modelo || []);
    renderPlantilla(tipo);
}

function renderPlantilla(tipo) {
    const estado = document.getElementById('estado-plantilla');
    const resultado = document.getElementById('plantilla-resultado');
    estado.textContent = tipo.tiene_plantilla_activa ? 'plantilla activa' : 'sin plantilla';
    estado.className = `badge ${tipo.tiene_plantilla_activa ? 'ok' : 'warn'}`;
    resultado.textContent = textoResumenPlantilla(tipo);
}

function textoResumenPlantilla(tipo) {
    if (!tipo.tiene_plantilla_activa) return 'Crea una plantilla desde el primer PDF validado.';
    return `${tipo.total_plantillas} plantilla(s) registradas. El detalle sensible se conserva solo en servidor.`;
}

function renderCampos(campos) {
    document.getElementById('resumen-campos').textContent = campos.length;
    const lista = document.getElementById('lista-campos');
    const select = document.getElementById('campo-anotacion');
    lista.innerHTML = '';
    select.innerHTML = '';
    campos.forEach(campo => agregarCampoVista(lista, select, campo));
    if (!campos.length) lista.innerHTML = '<div class="vacio">Agrega campos para entrenar.</div>';
}

function agregarCampoVista(lista, select, campo) {
    lista.innerHTML += `<div class="fila"><div class="fila-titulo"><strong>${campo.nombre}</strong><span class="badge ${campo.obligatorio ? 'ok' : ''}">${campo.etiqueta_entidad}</span></div><p class="muted">${campo.clave} - ${campo.tipo_dato || 'texto'}</p></div>`;
    select.appendChild(crearOpcionCampo(campo));
}

function crearOpcionCampo(campo) {
    const option = document.createElement('option');
    option.value = campo.clave;
    option.dataset.etiqueta = campo.etiqueta_entidad;
    option.textContent = `${campo.nombre} (${campo.etiqueta_entidad})`;
    return option;
}

function renderModelos(modelos) {
    const lista = document.getElementById('lista-modelos');
    lista.innerHTML = '';
    modelos.forEach(modelo => lista.appendChild(crearModeloVista(modelo)));
    if (!modelos.length) lista.innerHTML = '<div class="vacio">Sin versiones registradas.</div>';
}

function crearModeloVista(modelo) {
    const div = document.createElement('div');
    const clase = modelo.estado === 'activo' ? 'ok' : modelo.estado === 'rechazado' ? 'error' : 'warn';
    div.className = 'fila';
    div.innerHTML = `<div class="fila-titulo"><strong>${modelo.nombre_modelo}</strong><span class="badge ${clase}">${modelo.estado}</span></div><p class="muted">${modelo.documentos_entrenamiento || 0} documentos - F1 ${modelo.metricas?.f1_entidades ?? '-'}</p>`;
    return div;
}

async function cargarDocumentosEntrenamiento() {
    if (!tipoSeleccionado) return;
    try {
        const data = await apiJson(`/admin/tipos-documento/${tipoSeleccionado}/documentos-entrenamiento`, {admin:true});
        renderDocumentos(data.documentos_entrenamiento || []);
    } catch {
        document.getElementById('lista-documentos-entrenamiento').innerHTML = '<div class="vacio">Inicia sesion para listar documentos.</div>';
    }
}

function renderDocumentos(documentos) {
    document.getElementById('resumen-documentos').textContent = documentos.length;
    const lista = document.getElementById('lista-documentos-entrenamiento');
    lista.innerHTML = '';
    documentos.forEach(doc => lista.appendChild(crearDocumentoVista(doc)));
    if (!documentos.length) lista.innerHTML = '<div class="vacio">Sube un PDF para generar OCR.</div>';
}

function crearDocumentoVista(doc) {
    const boton = document.createElement('button');
    boton.type = 'button';
    boton.className = 'tipo';
    boton.innerHTML = `<strong>${doc.nombre_archivo}</strong><br><span class="muted">${doc.estado} - ${(doc.anotaciones || []).length} anotaciones</span>`;
    boton.onclick = () => seleccionarDocumentoEntrenamiento(doc);
    return boton;
}

function seleccionarDocumentoEntrenamiento(doc) {
    documentoEntrenamientoSeleccionado = doc.id_documento_entrenamiento;
    document.getElementById('texto-ocr-entrenamiento').value = doc.texto_ocr || '';
}

async function cargarLotes() {
    if (!tipoSeleccionado) return;
    try {
        const data = await apiJson(`/admin/aprendizaje/lotes?id_tipo_documento=${tipoSeleccionado}`, {admin:true});
        renderLotes(data.aprendizaje?.lotes || []);
    } catch {
        document.getElementById('lista-lotes').innerHTML = '<div class="vacio">Inicia sesion para ver lotes.</div>';
    }
}

function renderLotes(lotes) {
    document.getElementById('resumen-lotes').textContent = lotes.length;
    const lista = document.getElementById('lista-lotes');
    lista.innerHTML = '';
    lotes.forEach(lote => lista.appendChild(crearLote(lote)));
    if (!lotes.length) lista.innerHTML = '<div class="vacio">Aun no hay documentos validados recibidos.</div>';
    document.getElementById('resumen-decision').textContent = lotes[0]?.estado || '-';
}

function crearLote(lote) {
    const div = document.createElement('div');
    div.className = 'fila stack';
    div.innerHTML = htmlLote(lote);
    div.querySelector('button').onclick = () => entrenarLote(lote.id_lote);
    return div;
}

function htmlLote(lote) {
    return `<div class="fila-titulo"><div><strong>Lote ${lote.id_lote.slice(0,8)}</strong><p class="muted">${(lote.documentos || []).length} documentos - ${lote.estado}</p></div><button class="fantasma" type="button">Entrenar lote</button></div>${htmlMetricas(lote)}${htmlRecomendaciones(lote)}`;
}

function htmlMetricas(lote) {
    const comp = lote.decision?.comparacion || {};
    const cards = Object.entries(comp).map(([campo, datos]) => htmlMetrica(campo, datos)).join('');
    return cards ? `<div class="metricas">${cards}</div>` : '';
}

function htmlMetrica(campo, datos) {
    const clase = datos.resultado === 'mejoro' ? 'ok' : datos.resultado === 'empeoro' ? 'error' : 'warn';
    return `<div class="metric-card"><strong>${campo}</strong><p class="muted">F1 anterior ${datos.f1_anterior} - F1 candidato ${datos.f1_candidato}</p><span class="badge ${clase}">${datos.resultado}</span></div>`;
}

function htmlRecomendaciones(lote) {
    const recs = lote.recomendaciones || lote.decision?.recomendaciones || [];
    return recs.length ? `<div class="callout">${recs.join('<br>')}</div>` : '';
}

async function entrenarLote(idLote) {
    try {
        mostrarEstado('Entrenamiento enviado a cola.', '');
        await apiJson(`/admin/aprendizaje/lotes/${idLote}/entrenar`, {method:'POST', admin:true});
        await cargarLotes();
    } catch (error) {
        mostrarEstado(error.message, 'error');
    }
}

async function cargarApiKeys() {
    try {
        const data = await apiJson('/admin/api-keys', {admin:true});
        renderApiKeys(data.api_keys || []);
    } catch {
        document.getElementById('lista-api-keys').innerHTML = '<div class="vacio">Inicia sesion.</div>';
    }
    actualizarEjemplosApi();
}

function renderApiKeys(keys) {
    const lista = document.getElementById('lista-api-keys');
    lista.innerHTML = keys.map(key => `<div class="fila"><strong>${key.nombre}</strong><p class="muted">${key.prefijo}</p></div>`).join('') || '<div class="vacio">Sin API keys.</div>';
}

function actualizarEjemplosApi() {
    const base = window.location.origin;
    document.getElementById('ejemplo-curl').textContent = ejemploCurl(base);
    document.getElementById('ejemplo-js').textContent = ejemploJs(base);
}

function ejemploCurl(base) {
    return `curl -X POST "${base}/aprendizaje/documentos-validados" \\\n  -H "X-API-Key: ${ultimaApiKey}" \\\n  -F "id_tipo_documento=${tipoSeleccionado || 'constancia_servicio'}" \\\n  -F 'campos_validados={"alu_matricula":"2411367","NOMBRE_COMPLETO":"Juan Perez Lopez","alu_carrera":"Ingenieria","alu_servicio":"ENERO A JULIO"}' \\\n  -F "file=@constancia.pdf"`;
}

function ejemploJs(base) {
    return `const formData = new FormData();\nformData.append("file", archivoPdf);\nformData.append("id_tipo_documento", "${tipoSeleccionado || 'constancia_servicio'}");\nformData.append("campos_validados", JSON.stringify(datosCorregidos));\nawait fetch("${base}/aprendizaje/documentos-validados", { method: "POST", headers: { "X-API-Key": "${ultimaApiKey}" }, body: formData });`;
}

function abrirWizardTipo() {
    pasoTipo = 0;
    document.getElementById('modal-tipo').classList.add('activo');
    mostrarPasoTipo();
}

function cerrarWizardTipo() {
    document.getElementById('modal-tipo').classList.remove('activo');
}

function moverWizardTipo(direccion) {
    pasoTipo = Math.max(0, Math.min(3, pasoTipo + direccion));
    mostrarPasoTipo();
}

function mostrarPasoTipo() {
    document.querySelectorAll('.wizard-pagina').forEach(pagina => pagina.classList.toggle('activa', Number(pagina.dataset.paginaTipo) === pasoTipo));
    document.querySelectorAll('.paso-wizard').forEach((paso, indice) => paso.classList.toggle('activo', indice <= pasoTipo));
    actualizarResumenTipo();
}

function actualizarResumenTipo() {
    const datos = new FormData(document.getElementById('form-tipo'));
    document.getElementById('resumen-tipo').innerHTML = `<strong>${datos.get('nombre') || 'Sin nombre'}</strong><span>${datos.get('descripcion') || 'Sin descripcion'}</span><span>Estado: ${datos.get('estado') || 'borrador'}</span><span>Modelo inicial: ${datos.get('modelo_activo') || 'spacy_model'}</span>`;
}

async function crearTipoDesdeWizard(evento) {
    evento.preventDefault();
    const form = new FormData(evento.currentTarget);
    await apiJson('/admin/tipos-documento', {method:'POST', admin:true, body:JSON.stringify(datosTipo(form))});
    evento.currentTarget.reset();
    cerrarWizardTipo();
    await cargarTipos();
}

function datosTipo(form) {
    return {nombre:form.get('nombre'), descripcion:form.get('descripcion'), estado:form.get('estado'), modelo_activo:form.get('modelo_activo')};
}

async function enviarPlantilla(evento) {
    evento.preventDefault();
    const respuesta = await fetch(`/admin/tipos-documento/${tipoSeleccionado}/plantillas`, {method:'POST', body:new FormData(evento.currentTarget)});
    const data = await respuesta.json();
    if (!respuesta.ok) throw new Error(data.error || 'No se pudo crear la plantilla');
    renderPlantillaCreada(data.plantilla);
    await cargarTipos();
}

function renderPlantillaCreada(plantilla) {
    const campos = plantilla.campos || [];
    document.getElementById('plantilla-resultado').innerHTML = campos.map(campo => htmlCampoPlantilla(campo)).join('') || 'Plantilla creada sin campos ubicados.';
}

function htmlCampoPlantilla(campo) {
    const ubicacion = campo.ubicacion || {};
    return `<div class="fila"><strong>${campo.clave_campo}</strong><p class="muted">${campo.texto_detectado} - confianza ${campo.confianza}</p><p class="muted">x:${ubicacion.x}, y:${ubicacion.y}, ancho:${ubicacion.ancho}, alto:${ubicacion.alto}</p></div>`;
}

async function crearApiKey(evento) {
    evento.preventDefault();
    const form = new FormData(evento.currentTarget);
    const data = await apiJson('/admin/api-keys', {method:'POST', admin:true, body:JSON.stringify({nombre:form.get('nombre'), permisos:['extract']})});
    ultimaApiKey = data.api_key;
    document.getElementById('api-key-valor').textContent = data.api_key;
    document.getElementById('api-key-generada').style.display = 'grid';
    await cargarApiKeys();
}

async function crearCampo(evento) {
    evento.preventDefault();
    const form = new FormData(evento.currentTarget);
    await apiJson(`/admin/tipos-documento/${tipoSeleccionado}/campos`, {method:'POST', admin:true, body:JSON.stringify(datosCampo(form))});
    evento.currentTarget.reset();
    await cargarTipos();
}

function datosCampo(form) {
    return {nombre:form.get('nombre'), clave:form.get('clave'), etiqueta_entidad:form.get('etiqueta_entidad'), tipo_dato:form.get('tipo_dato'), obligatorio:form.get('obligatorio') === 'on', descripcion:form.get('descripcion')};
}

async function registrarModelo(evento) {
    evento.preventDefault();
    const form = new FormData(evento.currentTarget);
    await apiJson(`/admin/tipos-documento/${tipoSeleccionado}/modelos`, {method:'POST', admin:true, body:JSON.stringify(datosModelo(form))});
    evento.currentTarget.reset();
    await cargarTipos();
}

function datosModelo(form) {
    return {nombre_modelo:form.get('nombre_modelo'), ruta_modelo:form.get('ruta_modelo'), documentos_entrenamiento:Number(form.get('documentos_entrenamiento') || 0), activar:form.get('activar') === 'on', observaciones:form.get('observaciones'), metricas:{f1_entidades:Number(form.get('f1_entidades') || 0)}};
}

async function subirDocumentoEntrenamiento(evento) {
    evento.preventDefault();
    const respuesta = await fetch(`/admin/tipos-documento/${tipoSeleccionado}/documentos-entrenamiento`, {method:'POST', body:new FormData(evento.currentTarget)});
    const data = await respuesta.json();
    if (!respuesta.ok) throw new Error(data.error);
    document.getElementById('texto-ocr-entrenamiento').value = data.documento_entrenamiento.texto_ocr || '';
    await cargarDocumentosEntrenamiento();
}

function capturarSeleccionOcr(evento) {
    const texto = evento.currentTarget;
    if (texto.selectionEnd <= texto.selectionStart) return;
    rangoSeleccionado = {inicio:texto.selectionStart, fin:texto.selectionEnd};
    document.getElementById('texto-anotado').value = texto.value.substring(texto.selectionStart, texto.selectionEnd).trim();
}

async function guardarAnotacion() {
    const select = document.getElementById('campo-anotacion');
    const opcion = select.options[select.selectedIndex];
    await apiJson(`/admin/documentos-entrenamiento/${documentoEntrenamientoSeleccionado}/anotaciones`, {method:'POST', admin:true, body:JSON.stringify(datosAnotacion(select, opcion))});
    await cargarDocumentosEntrenamiento();
}

function datosAnotacion(select, opcion) {
    return {clave_campo:select.value, etiqueta_entidad:opcion.dataset.etiqueta, texto_anotado:document.getElementById('texto-anotado').value, posicion_inicio:rangoSeleccionado.inicio, posicion_fin:rangoSeleccionado.fin};
}