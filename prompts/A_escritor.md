# Opción A: Apache OpenOffice Writer → "Escritor UNAMAD"

## Prompt 1 (Interfaz)
Actúa como ingeniero de software. Con PyQt6 genera el esqueleto de un procesador de texto que replique
la disposición ergonómica observada por caja negra (sin copiar código ni íconos):
- Menús en español: Archivo, Editar, Ver, Insertar, Formato, Tabla, Herramientas, Ayuda.
- Dos barras apiladas: estándar (nuevo, abrir, guardar, PDF, imprimir, deshacer, rehacer, buscar) y formato
  (estilo, fuente, tamaño, N C S, 4 alineaciones, numeración, viñetas, color de texto y resaltado).
- Hoja blanca centrada sobre fondo gris y panel lateral acoplable a la derecha.
- Barra de estado: página, palabras y caracteres, idioma, modo INSERT y zoom con deslizador.
Los botones usan texto o íconos estándar de Qt. No incluyas lógica todavía.

## Prompt 2 (Lógica core)
Implementa la lógica con estos hallazgos de la Fase 2:
- El .odt es un ZIP: la primera entrada es `mimetype` SIN comprimir (application/vnd.oasis.opendocument.text),
  y además content.xml, styles.xml, meta.xml, settings.xml y META-INF/manifest.xml.
- La negrita no se guarda en el texto: se declara un estilo automático T1 (style:family="text",
  fo:font-weight="bold") y se referencia con <text:span text:style-name="T1">.
- meta.xml guarda meta:document-statistic (párrafos, palabras, caracteres).
- Process Monitor: escribe nombre0.odt y luego renombra sobre el destino (guardado atómico); crea `.~lock.nombre#`.
Escribe `odt.py` (leer/escribir entre QTextDocument y ODT, resolviendo herencia de estilos), guardado atómico,
candado, y apertura/guardado de .odt, .docx, .html y .txt. Incluye pruebas.

## Prompt 3 (Módulo IA)
Acopla IA local (Ollama: llama3.1:8b para estilo y resumen, llama3.2:3b para autocompletar) en un QThread con
streaming y cancelación: (a) corregir estilo de la selección mostrando la propuesta antes de reemplazar,
(b) resumir, (c) autocompletado contextual con Ctrl+Espacio que se acepta con Tab.
La interfaz nunca debe bloquearse. Maneja Ollama apagado, modelo ausente, tiempo de espera y texto vacío.
