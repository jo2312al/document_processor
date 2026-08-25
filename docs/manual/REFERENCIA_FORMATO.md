# Especificación visual y documental del manual de usuario

## Propósito y fuente de referencia

Esta especificación traduce al sistema actual los principios editoriales observados en `manual_desaca.pdf`. El documento de referencia tiene 52 páginas, formato carta vertical (612 × 792 pt), fue producido con LaTeX y combina páginas preliminares con numeración romana, cuatro capítulos operativos con numeración arábiga, 35 figuras, ocho tablas y una sección final de referencias.

Se replica su sistema de diseño —estructura, jerarquía, composición, ritmo, tratamiento de capturas y tablas— sin reutilizar nombres, textos, logotipos, datos personales ni identidad institucional de la publicación original.

## Alcance del nuevo manual

El manual documentará todo el producto para tres perfiles:

1. Persona usuaria del analizador público.
2. Persona administradora de la consola documental.
3. Persona integradora responsable del consumo de la API.

El contenido cubrirá acceso, extracción, administración de tipos documentales y campos, plantillas, anotación asistida, lotes, aprendizaje activo, modelos, claves API, integración, solución de problemas y prácticas de operación segura.

## Estructura

### Sección preliminar

- Portada exterior sobria.
- Portadilla con título completo, versión y propósito.
- Control documental con versión, fecha, responsable genérico y estado.
- Aviso de alcance y uso.
- Siglas y acrónimos.
- Índice de figuras.
- Índice de tablas.
- Índice general.

Las páginas preliminares utilizarán numeración romana en mayúsculas. No se incluirán directorios de personas, créditos institucionales extensos ni páginas legales heredadas de la referencia; se sustituirán por un control documental breve y pertinente al proyecto.

### Cuerpo principal

1. Introducción al sistema documental.
2. Acceso, perfiles y navegación.
3. Analizador público y extracción de documentos.
4. Configuración de tipos documentales y campos.
5. Plantillas y anotación asistida.
6. Aprendizaje, lotes y modelos.
7. Claves e integración API.
8. Solución de problemas y buenas prácticas.
9. Glosario y referencias técnicas.

Cada capítulo comenzará en página nueva. El primer texto de un capítulo explicará su finalidad antes de entrar en procedimientos, siguiendo el patrón contextual de la referencia.

## Diseño

### Página

- Tamaño: carta, orientación vertical.
- Márgenes nominales: 19 mm superior, 18 mm inferior, 22 mm interior y 19 mm exterior.
- Área útil: una columna principal de lectura y una franja exterior reservada para identificación de capítulo.
- Texto alineado a la izquierda, sin depender de justificación forzada en párrafos cortos.
- Separación generosa entre bloques; ninguna página se llenará hasta el borde inferior.
- Capturas y tablas se mantendrán con el texto que las introduce siempre que la paginación lo permita.

### Encabezado

- En páginas ordinarias: título de sección a la izquierda y marca gráfica propia del proyecto a la derecha.
- Regla horizontal fina en azul grisáceo debajo del encabezado.
- Sin encabezado en portada, portadilla ni aperturas principales de capítulo.

### Pie y numeración

- Número de página dentro de una pastilla azul oscuro situada en el borde exterior.
- Numeración romana para preliminares y arábiga para el cuerpo.
- En páginas de capítulo, la pastilla se integra con la composición de apertura.
- El pie no contendrá nombres ni datos del documento de referencia.

### Elemento lateral

En páginas interiores se utilizará una banda vertical gris muy clara en el margen exterior con el nombre abreviado del capítulo. El recurso replica la navegación lateral del manual de referencia sin copiar su rotulación.

## Tipografía

La referencia combina una serif editorial para títulos y cuerpo con sans serif para navegación y tablas. Se utilizarán fuentes disponibles y compatibles:

- Títulos de capítulo: Cambria, 24–28 pt, negrita.
- Número de capítulo: Cambria, 46–54 pt, negro, con regla vertical verde.
- Título de sección: Aptos o Arial, 15–17 pt, negrita, azul oscuro.
- Subsección: Aptos o Arial, 11–13 pt, negrita, verde oscuro.
- Cuerpo: Cambria, 9.5–10 pt, interlineado aproximado de 1.12.
- Tablas y recuadros: Aptos o Arial, 8–9 pt.
- Pies de figura y tabla: Cambria, 8 pt; etiqueta y número en negrita.
- Encabezado y banda lateral: Aptos o Arial, 7.5–8.5 pt.

La jerarquía se aplicará mediante estilos reales de Word. No se simularán títulos, listas ni numeraciones con formato manual.

## Colores

Paleta adaptada a la identidad disponible en el proyecto (`img/tecnm.png` e `img/itvh.png`) y a la lógica de la referencia:

| Rol | Color | Uso |
|---|---:|---|
| Azul principal | `#173B67` | Portada, pastillas de página, cabeceras de tabla |
| Azul profundo | `#0A1E4D` | Títulos fuertes y navegación lateral |
| Azul de interfaz | `#0E7490` | Acentos vinculados con la aplicación |
| Verde de acento | `#77933C` | Reglas, números secundarios y secciones |
| Gris de fondo | `#F1F2F0` | Banda lateral, filas alternas y recuadros |
| Gris de borde | `#B8BDC5` | Bordes de tablas y contenedores |
| Amarillo de aviso | `#F4DE72` | Etiqueta IMPORTANTE |
| Rojo de advertencia | `#B42318` | Etiqueta ADVERTENCIA y estados críticos |
| Negro editorial | `#171717` | Texto principal |

El azul institucional domina; el verde se reserva para señalización jerárquica. Los colores de estado visibles en las capturas no se reinterpretarán.

## Capítulos

La apertura de cada capítulo reproducirá la composición característica observada:

- Número grande en el tercio superior izquierdo.
- Regla vertical verde inmediatamente después del número.
- Título del capítulo alineado con el centro óptico del número.
- Pastilla azul con el número de página en el borde exterior.
- Introducción de uno a tres párrafos.
- Banda lateral en páginas posteriores con el título abreviado del capítulo.

Los títulos se numerarán como `3`, `3.1` y `3.1.1`. Los procedimientos usarán pasos numerados reales y verbos de acción directos.

## Figuras

- Numeración por capítulo: `Figura 3.1`, `Figura 3.2`, etc.
- Secuencia editorial: explicar la acción, citar la figura en el párrafo, insertar la captura y agregar el pie.
- Capturas centradas, con ancho habitual de 75–92 % de la columna y borde gris de 0.5 pt.
- Las capturas pequeñas o los mensajes modales podrán agruparse como subfiguras `(a)`, `(b)` y `(c)` cuando formen una secuencia.
- El pie se colocará debajo, centrado, con punto después del número.
- Las capturas se obtendrán de la aplicación real y se guardarán en `docs/manual/capturas/` con nombres estables y descriptivos.
- Se evitarán capturas redundantes; cada imagen deberá enseñar una decisión, estado o resultado concreto.
- Datos sensibles, claves y rutas privadas se ocultarán o sustituirán por valores de demostración.

## Tablas

- Numeración por capítulo: `Tabla 4.1`, `Tabla 4.2`, etc.
- Título o encabezado superior en azul principal con texto blanco.
- Primera fila de columnas en azul oscuro o gris azulado.
- Filas alternas en blanco y gris claro.
- Bordes finos grises; sin cuadrícula visualmente pesada.
- Texto de 8–9 pt y relleno interno suficiente para evitar densidad excesiva.
- Pie de tabla debajo, con etiqueta y número en negrita.
- Uso principal: campos de formularios, botones, estados, permisos, reglas, endpoints, parámetros y respuestas.
- Anchos de columna explícitos; las descripciones tendrán mayor proporción que nombres o iconos.

## Recuadros

### IMPORTANTE

- Etiqueta amarilla con texto negro en negrita.
- Cuerpo sobre fondo gris muy claro.
- Uso: reglas cuya omisión impide completar una operación o compromete el aprendizaje del modelo.

### NOTA

- Etiqueta azul de interfaz con texto blanco.
- Cuerpo sobre fondo azul muy pálido.
- Uso: contexto complementario, alternativas y aclaraciones.

### ADVERTENCIA

- Etiqueta roja con texto blanco.
- Borde izquierdo rojo de 2–3 pt y fondo rosado muy claro.
- Uso: pérdida potencial de datos, exposición de claves, activación incorrecta de modelos o acciones difíciles de revertir.

Los tres componentes conservarán la misma geometría, tipografía y espaciado a lo largo del documento.

## Procedimientos y tono

- Español claro, formal y operativo.
- Instrucciones dirigidas a la persona usuaria, con lenguaje neutral.
- Un objetivo observable por procedimiento.
- Requisitos previos antes de los pasos cuando sean necesarios.
- Cada paso describirá acción y resultado esperado.
- Los nombres visibles de botones, pestañas y campos aparecerán en negrita.
- Los endpoints, nombres de archivo y valores técnicos se presentarán en estilo monoespaciado.
- Mensajes de error y estados se documentarán sin inventar comportamientos no respaldados por el código o la interfaz.

## Adaptaciones y exclusiones

No se trasladarán los siguientes elementos de la referencia:

- Logotipos, nombres, cargos, directorios y datos de contacto originales.
- Textos legales, licencia, ISBN o referencias institucionales ajenas al proyecto.
- Capítulos temáticos sobre diplomados y procesos que no pertenecen al sistema actual.
- Capturas, iconos o ejemplos del sistema SRSD.
- Doble portadilla extensa y páginas en blanco editoriales que no aporten al uso digital.

Se conservarán, adaptados al producto:

- Portada formal y páginas preliminares.
- Índices especializados.
- Numeración romana y arábiga por secciones.
- Aperturas de capítulo con número dominante.
- Navegación lateral.
- Relación sistemática entre explicación, figura y pie.
- Tablas para describir controles y reglas.
- Recuadros de información importante.
- Densidad moderada, espacios en blanco y composición editorial.

## Entregables y control de calidad

El proceso producirá:

- `docs/manual/manual-usuario.docx` como fuente editable.
- `docs/manual/manual-usuario.pdf` como entrega final diagramada.
- `docs/manual/capturas/` con las imágenes utilizadas.

Antes de la entrega se realizarán estas verificaciones:

1. Recorrido de los flujos reales del analizador, consola e integración.
2. Renderizado completo del DOCX a imágenes.
3. Inspección visual página por página del DOCX renderizado.
4. Exportación del PDF y renderizado completo a PNG.
5. Comparación visual por muestras y por estructura contra las 52 páginas de referencia.
6. Revisión de índices, numeración, pies, tablas, encabezados, saltos de capítulo, legibilidad de capturas y ausencia de contenido sensible.
7. Corrección y nuevo renderizado hasta eliminar defectos de superposición, recorte, páginas huérfanas o inconsistencias.

El resultado solo se considerará terminado cuando sea evidente su parentesco editorial con la referencia y no presente el aspecto de Markdown exportado sin diagramación.
