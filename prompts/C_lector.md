# Opción C: SumatraPDF → "Lector UNAMAD"

## Prompt 1 (Interfaz)
Con PyQt6 genera un visor minimalista con la barra observada en el árbol UIA de SumatraPDF, en este orden:
Abrir, Imprimir | Página [n] / total, anterior, siguiente | Ajustar al ancho, Una página, Girar izq., Girar der.,
Reducir, Ampliar | Buscar [texto], anterior, siguiente, coincidir mayúsculas. Pestañas por documento y panel de
marcadores a la izquierda.

## Prompt 2 (Lógica core)
Con PyMuPDF: renderizado perezoso de las páginas visibles en modo continuo, zoom, rotación, búsqueda con resaltado,
índice y favoritos. Atajos observados: Ctrl+O, Ctrl+P, N, P, F3, Shift+F3, Ctrl++ y Ctrl+-.
Persistencia como en SumatraPDF-settings.txt: por archivo FilePath, PageNo, Zoom, Rotation, DisplayMode y Favorites.
Process Monitor mostró una sola escritura de configuración y que el PDF se abre para lectura.

## Prompt 3 (Módulo IA)
Panel "Chat con el PDF" (RAG local): fragmentar por página con solapamiento, embeddings bge-m3 vía Ollama con índice en
caché, recuperación por similitud coseno y respuesta en streaming con llama3.1:8b citando [pág. N], negándose si el dato
no está. Todo en QThread y cancelable. Al hacer clic en una cita salta a la página. Maneja PDF sin texto y Ollama apagado.
