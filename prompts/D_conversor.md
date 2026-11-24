# Opción D: IrfanView → "Conversor UNAMAD"

## Prompt 1 (Interfaz)
Con PyQt6 genera un visor/conversor con la disposición observada en IrfanView: menús Archivo/Editar/Imagen/Ver/Ayuda,
área de imagen central y diálogo de conversión por lotes (tecla B) con lista de archivos, formato de salida,
redimensionado, calidad y carpeta destino. Barra de estado: tamaño, profundidad de bits, posición n/m, zoom y peso.

## Prompt 2 (Lógica core)
Con Pillow: identificar el formato por número mágico (BM, FF D8 FF, 89 50 4E 47, GIF8, II/MM TIFF, RIFF WEBP) sin
confiar en la extensión; convertir BMP/JPG/PNG/GIF/TIF/WEBP; JPEG con submuestreo 4:2:0; redimensionar con Lanczos;
girar (L/R), voltear (H/V), negativo, gris; navegar por la carpeta (Espacio/Retroceso); lotes en segundo plano.
Process Monitor mostró que IrfanView escribe directo sobre el destino: mejóralo con salida atómica.

## Prompt 3 (Módulo IA)
Clasificación zero-shot de fauna y flora amazónica con CLIP ViT-B/32 (ONNX Runtime, local): etiquetas en español con
prompts en inglés, varias plantillas promediadas, embeddings de texto en caché y umbral de confianza. En el lote debe
poder ordenar las salidas en subcarpetas por especie y generar un CSV. Sin bloquear la UI y con errores por archivo.
