import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, Ellipse
from pathlib import Path
F = Path(__file__).parent/"fig"; V = "#065f46"; G = "#e6f2ee"; N = "#fff4d6"
plt.rcParams["font.family"] = "Segoe UI"
def caja(ax, x, y, t, w=2.3, h=.8, c=G): 
    ax.add_patch(FancyBboxPatch((x-w/2, y-h/2), w, h, boxstyle="round,pad=.04", fc=c, ec=V, lw=1.3)); ax.text(x, y, t, ha="center", va="center", fontsize=8.6)
def fle(ax, a, b, t="", curva=0, dy=.13):
    ax.annotate("", xy=b, xytext=a, arrowprops=dict(arrowstyle="->", color="#333", lw=1.2, connectionstyle=f"arc3,rad={curva}"))
    if t: ax.text((a[0]+b[0])/2, (a[1]+b[1])/2+dy, t, ha="center", fontsize=7.6, color="#333")
def lienzo(w, h, X, Y):
    f, ax = plt.subplots(figsize=(w, h)); ax.set_xlim(0, X); ax.set_ylim(0, Y); ax.axis("off"); return f, ax
def guarda(f, n): f.savefig(F/n, dpi=170, bbox_inches="tight"); plt.close(f)
def flujo(n, pasos, ia, salida):
    f, ax = lienzo(8.2, 2.9, 12.4, 4.2)
    xs = [1.4, 4.6, 7.8, 11]
    for x, t in zip(xs, pasos): caja(ax, x, 3.2, t)
    for a, b in zip(xs, xs[1:]): fle(ax, (a+1.22, 3.2), (b-1.22, 3.2))
    caja(ax, 4.6, 1.1, ia, 3.0, .95, N); caja(ax, 9.4, 1.1, salida, 3.4, .95)
    fle(ax, (4.6, 2.75), (4.6, 1.65), "hilo aparte", dy=0); fle(ax, (6.2, 1.2), (7.5, 2.72)); fle(ax, (11, 2.75), (9.9, 1.65)); guarda(f, n)
flujo("flujo_A.png", ["Abrir .odt\n(ZIP, candado)", "Editar\n(estilos T/P)", "Contar y\nprevisualizar", "Guardar"], "IA: corregir, resumir,\nautocompletar (Llama 3)", "Temporal → renombrar\n(guardado atómico)")
flujo("flujo_B.png", ["Abrir imagen\n→ RGBA", "Dibujar\n(x, y)", "Vista previa,\nzoom", "Guardar"], "IA: U²-Net (fondo)\ny CLIP (bocetos)", "PNG tipo 6 + pHYs\n(guardado atómico)")
flujo("flujo_C.png", ["Abrir PDF\n(solo lectura)", "Renderizar\nvisibles", "Buscar, zoom,\nrotar", "Cerrar"], "IA: RAG (bge-m3 +\nLlama 3.1) con citas", "Estado por archivo:\npágina, zoom, rotación")
flujo("flujo_D.png", ["Leer número\nmágico", "Decodificar\n(Pillow)", "Transformar,\nlote", "Convertir"], "IA: CLIP zero-shot\n(fauna y flora)", "Subcarpeta por especie\n+ CSV (salida atómica)")
def casos(n, titulo, cs):
    f, ax = lienzo(3.9, 3.3, 6, 5.6)
    ax.add_patch(plt.Circle((.6, 3.3), .22, fc="white", ec=V, lw=1.4))
    for a, b in (((.6, 3.08), (.6, 2.4)), ((.25, 2.85), (.95, 2.85)), ((.6, 2.4), (.3, 1.9)), ((.6, 2.4), (.9, 1.9))): ax.plot(*zip(a, b), c=V, lw=1.4)
    ax.text(.6, 1.55, "Usuario", ha="center", fontsize=8); ax.text(3.8, 5.35, titulo, ha="center", fontsize=9, weight="bold", color=V)
    for i, c in enumerate(cs):
        y = 4.7-i*.83; ax.add_patch(Ellipse((3.8, y), 3.7, .66, fc=N if c.startswith("IA") else G, ec=V)); ax.text(3.8, y, c, ha="center", va="center", fontsize=7.8); ax.plot([1, 1.95], [2.85, y], c="#777", lw=.8)
    guarda(f, n)
casos("casos_A.png", "A. Escritor", ["Abrir / guardar ODT, DOCX", "Dar formato", "Buscar y reemplazar", "Exportar PDF / imprimir", "IA: corregir y resumir", "IA: autocompletar"])
casos("casos_B.png", "B. Lienzo", ["Abrir / guardar imagen", "Dibujar y rellenar", "Insertar formas", "Recortar, girar, escalar", "IA: quitar fondo", "IA: reconocer boceto"])
casos("casos_C.png", "C. Lector", ["Abrir y navegar PDF", "Zoom y rotación", "Buscar texto", "Marcar favoritos", "IA: preguntar al PDF", "IA: saltar a la cita"])
casos("casos_D.png", "D. Conversor", ["Ver y navegar carpeta", "Leer cabecera", "Transformar imagen", "Convertir por lotes", "IA: identificar especie", "IA: ordenar por especie"])
f, ax = lienzo(8.4, 4.3, 12.4, 6.6)
for x, t in zip([1.5, 4.6, 7.7, 10.8], ["Escritor\n(PyQt6)", "Lienzo\n(PyQt6)", "Lector\n(PyQt6)", "Conversor\n(PyQt6)"]): caja(ax, x, 5.8, t)
for x, t in zip([1.5, 4.6, 7.7, 10.8], ["odt.py, formatos.py\n(lxml, python-docx)", "motor.py\n(Pillow, NumPy)", "Vista, rag.py\n(PyMuPDF)", "nucleo.py\n(Pillow, struct)"]): caja(ax, x, 4.3, t, 2.6); fle(ax, (x, 5.35), (x, 4.75))
caja(ax, 2.2, 2.6, "comun/archivos.py\nguardado atómico", 2.9); caja(ax, 6.2, 2.6, "comun/ia.py · Tarea (QThread)\nseñales avance / lista / fallo", 3.9); caja(ax, 10.4, 2.6, "comun/vision.py\nONNX Runtime", 2.9)
for x in (1.5, 4.6, 7.7, 10.8): fle(ax, (x, 3.85), (6.2+(x-6.2)*.25, 3.07))
caja(ax, 4.2, .8, "Ollama (local): llama3.1:8b,\nllama3.2:3b, bge-m3", 3.6, .95, N); caja(ax, 9.9, .8, "Modelos ONNX: CLIP ViT-B/32,\nU²-Net", 3.6, .95, N)
fle(ax, (5.7, 2.15), (4.5, 1.35)); fle(ax, (10.3, 2.15), (10, 1.35)); fle(ax, (8.2, 2.6), (8.9, 2.6)); guarda(f, "componentes.png")
# árbol UIA como figura (texto literal de la inspección)
E = F.parent.parent/"evidencias"
for k, n, desde in (("A_writer", 26, 0), ("B_paint", 34, 24), ("C_sumatra", 34, 0), ("D_irfanview", 22, 0)):
    ls = [l.rstrip()[:95] for l in (E/k/"arbol_uia.txt").read_text(encoding="utf8").split("\n")][desde:desde+n]
    f = plt.figure(figsize=(7.4, .118*len(ls)+.15)); f.patch.set_facecolor("#f7f7f7"); f.text(.01, .985, "\n".join(ls), family="Consolas", fontsize=7.2, va="top"); f.savefig(F/f"arbol_{k[0]}.png", dpi=170); plt.close(f)
