# Opción B: Microsoft Paint → "Lienzo UNAMAD"

## Prompt 1 (Interfaz)
Con PyQt6 genera el esqueleto de un editor gráfico con la disposición observada en el árbol UIA de Paint:
menús Archivo/Editar/Ver; cinta con los grupos Selección, Imagen (Recortar, Quitar fondo, Girar, Voltear, Cambiar de
tamaño), Herramientas (Lápiz, Relleno, Texto, Borrador, Selector de colores), Pinceles, Formas (Línea, Elipse,
Rectángulo, Rectángulo redondeado, Triángulo, Diamante, Pentágono, Hexágono, Flecha) y Colores (2 filas de 10);
deslizadores de grosor y opacidad a la izquierda; barra de estado con cursor (x,y), selección, tamaño y zoom.

## Prompt 2 (Lógica core)
Lienzo QImage ARGB32 de 1152×720; previsualización de formas al arrastrar, relleno por inundación, cuentagotas,
selección y recorte, girar, voltear, redimensionar, deshacer/rehacer (Ctrl+Z / Ctrl+Y) y zoom.
Guardado PNG/JPG/BMP compatible con lo observado: PNG tipo de color 6 (RGBA aunque la entrada fuese RGB), pHYs,
y escritura atómica (Process Monitor: %TEMP% y luego renombrado al destino).

## Prompt 3 (Módulo IA)
Acopla sin bloquear la UI (QThread): (a) quitar fondo con U²-Net en ONNX Runtime aplicando la máscara al canal alfa;
(b) reconocimiento de bocetos a mano alzada con CLIP zero-shot, devolviendo 5 etiquetas con probabilidad.
Maneja modelo ausente y lienzo vacío. El resultado debe poder deshacerse con Ctrl+Z.
