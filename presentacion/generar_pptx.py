"""Presentación para exponer en clase, con notas del orador. Las cifras salen de evidencias/resultados."""
import json
from pathlib import Path

from PIL import Image
from pptx import Presentation
from pptx.dml.color import RGBColor as C
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.util import Inches as I, Pt

R = Path(__file__).resolve().parent.parent
E, F = R / "evidencias", R / "informe/fig"
ia = json.load(open(E / "resultados/ia_final.json", encoding="utf8"))
cm = json.load(open(E / "resultados/comparativa.json", encoding="utf8"))
rd = cm["rendimiento"]
V, G, N, B = C(6, 95, 70), C(230, 242, 238), C(40, 40, 40), C(255, 255, 255)
pr = Presentation()
pr.slide_width, pr.slide_height = I(13.333), I(7.5)
num = lambda x: str(x).replace(".", ",")
pct = lambda x: f"{100 * x:.1f}".replace(".", ",") + " %"


def texto(s, x, y, w, h, t, tam=20, neg=False, col=N, al=None, ancla=None):
    tf = s.shapes.add_textbox(I(x), I(y), I(w), I(h)).text_frame
    tf.word_wrap = True
    if ancla:
        tf.vertical_anchor = ancla
    for i, l in enumerate(t if isinstance(t, list) else [t]):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.space_after = Pt(8)
        if al:
            p.alignment = al
        for j, parte in enumerate(l.split("**")):
            r = p.add_run()
            r.text = parte
            r.font.size, r.font.bold, r.font.color.rgb, r.font.name = Pt(tam), neg or j % 2 == 1, col, "Segoe UI"
    return tf


def lam(titulo, notas):
    s = pr.slides.add_slide(pr.slide_layouts[6])
    b = s.shapes.add_shape(1, 0, 0, I(.22), pr.slide_height)
    b.fill.solid()
    b.fill.fore_color.rgb = V
    b.line.fill.background()
    texto(s, .6, .35, 12.2, .9, titulo, 30, True, V)
    texto(s, .6, 6.98, 9, .35, "UNAMAD | Inteligencia Artificial | Jorge Antonio Diaz Ancco", 11, col=C(120, 120, 120))
    texto(s, 12.2, 6.98, .7, .35, str(len(pr.slides)), 11, col=C(120, 120, 120), al=PP_ALIGN.RIGHT)
    s.notes_slide.notes_text_frame.text = notas
    return s


def img(s, ruta, x, y, w, h):
    a, b = Image.open(ruta).size
    k = min(w / a, h / b)
    s.shapes.add_picture(str(ruta), I(x + (w - a * k) / 2), I(y + (h - b * k) / 2), I(a * k), I(b * k))


def tabla(s, x, y, w, filas, anchos, tam=15, alto=.5):
    t = s.shapes.add_table(len(filas), len(filas[0]), I(x), I(y), I(w), I(alto * len(filas))).table
    for j, a in enumerate(anchos):
        t.columns[j].width = I(w * a / sum(anchos))
    for i, f in enumerate(filas):
        for j, c in enumerate(f):
            k = t.cell(i, j)
            k.text = str(c)
            k.vertical_anchor = MSO_ANCHOR.MIDDLE
            k.fill.solid()
            k.fill.fore_color.rgb = V if i == 0 else (G if i % 2 else B)
            for p in k.text_frame.paragraphs:
                for r in p.runs:
                    r.font.size, r.font.bold, r.font.name = Pt(tam), i == 0, "Segoe UI"
                    r.font.color.rgb = B if i == 0 else N


s = pr.slides.add_slide(pr.slide_layouts[6])
f = s.background.fill
f.solid()
f.fore_color.rgb = V
texto(s, 1, .8, 11.3, .6, "UNIVERSIDAD NACIONAL AMAZÓNICA DE MADRE DE DIOS", 20, True, G, PP_ALIGN.CENTER)
texto(s, 1, 2.2, 11.3, 1.8, "Ingeniería inversa de cuatro programas y reconstrucción con IA", 42, True, B, PP_ALIGN.CENTER)
texto(s, 1, 4.1, 11.3, .6, "OpenOffice Writer · Microsoft Paint · SumatraPDF · IrfanView", 22, col=G, al=PP_ALIGN.CENTER)
texto(s, 1, 5.4, 11.3, 1.4, ["Jorge Antonio Diaz Ancco (22221038)", "Docente: Miguel Ángel Alatrista Aguilar", "Inteligencia Artificial, noviembre de 2026"], 18, col=B, al=PP_ALIGN.CENTER)
s.notes_slide.notes_text_frame.text = "Saludo y presentación (30 s). Estudié cuatro programas por observación, sin descompilar, y reconstruí cada uno en Python con IA local."

s = lam("Cuatro programas: dos open source y dos propietarios", "Un programa por cada categoría de la guía. Dos son de código abierto y dos de licencia propietaria, como pide el enunciado.")
tabla(s, .6, 1.5, 12.1, [["", "Original", "Licencia", "Réplica", "IA local añadida"],
      ["A", "OpenOffice Writer 4.1.17", "Open source (Apache 2.0)", "Escritor", "Corregir, resumir, autocompletar"],
      ["B", "Microsoft Paint 11", "Comercial", "Lienzo", "Quitar fondo, reconocer bocetos"],
      ["C", "SumatraPDF 3.6.1", "Open source (GPL-3.0)", "Lector", "Chat con el PDF (RAG)"],
      ["D", "IrfanView 4.76", "Propietaria, gratuita", "Conversor", "Clasificar fauna y flora amazónica"]], [.4, 2.6, 2.6, 1.4, 3.6], 17, .8)

s = lam("Método: cuatro fases, sin descompilar", "Caja negra: lo que se ve. Caja gris: lo que escribe en disco y la estructura de sus archivos. La guía prohíbe descompilar binarios protegidos; no se hizo.")
for i, (t, d) in enumerate((("1. Caja negra", "Árbol de interfaz con UI Automation, menús y atajos"), ("2. Archivos y E/S", "Hexadecimal, ZIP/XML, ExifTool y Process Monitor"),
                            ("3. Prompts", "Interfaz, lógica e IA: 3 por programa, 12 en total"), ("4. Pruebas", "52 automáticas y comparación con el original"))):
    b = s.shapes.add_shape(5, I(.6 + 3.08 * i), I(1.8), I(2.85), I(3.2))
    b.fill.solid()
    b.fill.fore_color.rgb = G
    b.line.color.rgb = V
    texto(s, .75 + 3.08 * i, 2.1, 2.55, .6, t, 21, True, V, PP_ALIGN.CENTER)
    texto(s, .75 + 3.08 * i, 2.95, 2.55, 1.8, d, 18, al=PP_ALIGN.CENTER)
texto(s, .6, 5.5, 12, .8, "Interfaz inspeccionada: 214 nodos en Writer, 232 en Paint, 45 en SumatraPDF, 41 nodos y 265 elementos de menú en IrfanView.", 18)

for op, nom, k, cap, pts, nota in (
    ("A", "Writer guarda un ZIP y la negrita es un estilo", "A_writer", "ventana_original.png",
     ["El .odt es un **ZIP** con 17 entradas", "La primera, **mimetype**, va sin comprimir", "La negrita es el estilo **T1**, no está en el texto", "Guarda en **nombre0.odt** y renombra (atómico)", "Crea el candado **.~lock.nombre#**"],
     "Mostrar el .odt renombrado a .zip. Explicar guardado atómico: si se corta la luz, el archivo anterior sigue intacto."),
    ("B", "Paint convierte el PNG a RGBA al guardar", "B_paint", "ventana_original.png",
     ["Mismo dibujo de 10×10: **76 a 537 bytes**", "Tipo de color **2 (RGB) pasa a 6 (RGBA)**", "Agrega **sRGB, gAMA, pHYs y XMP**", "Guarda en **%TEMP%** y renombra", "Ya trae módulos llamados AIServices y PaintAIManager"],
     "El byte 25 del PNG indica el tipo de color: 2 es RGB y 6 es RGBA. Se ve en el volcado hexadecimal."),
    ("C", "SumatraPDF: dos binarios y una sola escritura", "C_sumatra", "ventana_original.png",
     ["Solo **SumatraPDF.exe** y **libmupdf.dll**", "El PDF se abre **solo para lectura**", "Escribe únicamente **SumatraPDF-settings.txt**", "Recuerda página, zoom y rotación por archivo", "Un PDF se lee **desde el final** (xref, %%EOF)"],
     "Por eso es tan ligero: 20 MB y 0,11 s de arranque. El motor es MuPDF."),
    ("D", "IrfanView reconoce formatos por su número mágico", "D_irfanview", "ventana_original.png",
     ["BMP **42 4D**, JPG **FF D8 FF**, PNG **89 50 4E 47**", "JPG con submuestreo **4:2:0**", "Menú de **265 elementos**", "Escribe **directo** sobre el destino (sin temporal)", "Lee su .ini **464 veces** en una sesión"],
     "Cambiar la extensión no engaña al programa: lo que manda son los primeros bytes. La réplica mejora el guardado haciéndolo atómico."),
):
    s = lam(f"{op}. {nom}", nota)
    img(s, E / k / cap, .6, 1.45, 6.4, 5.2)
    texto(s, 7.3, 1.6, 5.5, 5, pts, 21)

s = lam("De los hallazgos al código: prompts y errores reales", "Aquí está lo importante: el primer código generado no bastaba. Cada error se encontró midiendo contra el original o con datos. Explicar dos a elección.")
tabla(s, .6, 1.45, 12.1, [["Error encontrado", "Causa", "Corrección y efecto"],
      ["Tucán y caimán con 0 aciertos", "Modelo cuantizado a 8 bits", "Pasar a fp32: 60 % a 82 %"],
      ["RAG tardaba 12,8 s", "Dos modelos se turnaban la VRAM", f"Embeddings en CPU: {num(round(ia['rag']['s_mediana'], 1))} s"],
      ["RAG leía otra fila de la tabla", "Texto plano sin columnas", "Un fragmento por fila"],
      ["660 MB de memoria", "OpenBLAS reserva por hilo", "Un hilo: unos 50 MB"],
      ["DOCX a 11 pt en Writer", "Faltaba la fuente base", "12 pt verificado en Writer"],
      ["Fotos con etiqueta falsa", "Nombre ambiguo («Ara»)", "Auditoría por taxonomía"]], [3, 3.2, 3.4], 16, .68)

s = lam("Arquitectura: la IA corre en otro hilo", "QThread y señales: avance, lista y fallo. Una prueba automática confirma que la interfaz nunca se detiene más de 300 ms. Si Ollama está apagado se muestra un mensaje.")
img(s, F / "componentes.png", 1.4, 1.35, 10.4, 5.5)

for t, k, n in (("Escritor: corrige y espera aprobación", "A_writer/replica_ia.png", "DEMO en vivo: escribir con errores, F7, revisar y reemplazar; luego Ctrl+Espacio y Tab para autocompletar. Si algo falla, usar esta captura."),
                ("Lector: responde con cita y admite cuando no sabe", "C_sumatra/replica_rag.png", "DEMO en vivo: abrir la guía y preguntar «¿Qué módulo de IA pide la opción C?» y luego algo que no está. Hacer clic en la cita.")):
    s = lam(t, n)
    img(s, E / k, .6, 1.3, 12.1, 5.6)
s = lam("Lienzo: quita el fondo y reconoce bocetos", "DEMO en vivo: abrir un jaguar, Quitar fondo, Ctrl+Z. Nuevo, dibujar un gato y Reconocer boceto.")
img(s, E / "B_paint/replica_fondo.png", .5, 1.5, 6.1, 5)
img(s, E / "B_paint/replica_boceto.png", 6.8, 1.5, 6.1, 5)
s = lam("Conversor: identifica la especie y ordena el lote", "DEMO en vivo: abrir una foto, tecla E; tecla B, marcar clasificar e iniciar.")
img(s, E / "D_irfanview/replica_especie.png", .5, 1.4, 6.6, 5.3)
img(s, E / "D_irfanview/replica_lote.png", 7.3, 1.4, 5.6, 5.3)

f_, b_, r_, c_ = ia["fauna"], ia["bocetos"], ia["rag"], ia["corrector"]
s = lam("Precisión medida con datos nuevos", "Datos distintos de los usados para ajustar. En fauna eran 82,2 % antes de auditar etiquetas. Muestras pequeñas: son cifras orientativas. El corrector a veces cambia el sentido, por eso hay vista previa.")
tabla(s, .6, 1.6, 12.1, [["Módulo", "Datos", "Resultado", "Latencia"],
      ["Fauna y flora", f"{f_['n']} fotos, 19 clases", f"{pct(f_['top1'])} (entre 3: {pct(f_['top3'])})", f"{f_['ms']:.0f} ms"],
      ["Bocetos", f"{b_['n']} dibujos, 23 clases", f"{pct(b_['top1'])} (entre 3: {pct(b_['top3'])})", f"{b_['ms']:.0f} ms"],
      ["Chat con PDF", f"{r_['n']} preguntas", f"{r_['aciertos']}/{r_['n']} y {r_['citas_ok']}/{r_['con_cita']} citas correctas", f"{num(round(r_['s_mediana'], 1))} s"],
      ["Corrector", "14 correcciones", f"{c_['corregidos']}/{c_['total']}", f"{num(round(c_['s_mediana'], 2))} s"]], [2, 2.6, 4, 1.5], 19, .85)

s = lam("Original frente a réplica", "Ser honesto: los programas nativos arrancan más rápido y gastan menos, salvo Paint en memoria. La ventaja de la réplica es la capacidad nueva. Con CLIP cargado la memoria sube a unos 690 MB.")
q = lambda k, x: num(rd[k][x])
tabla(s, .6, 1.5, 12.1, [["", "Arranque", "Memoria", "Interoperabilidad comprobada"]] + [
      [n, f"{q(o + '_original', 'arranque_s')} s / {q(o + '_replica', 'arranque_s')} s", f"{q(o + '_original', 'privada_mb')} / {q(o + '_replica', 'privada_mb')} MB", t]
      for o, n, t in (("A", "Writer / Escritor", "Writer abre su ODT y DOCX y reconoce el formato"), ("B", "Paint / Lienzo", "Paint abre PNG, BMP y JPG con el tamaño exacto"),
                      ("C", "SumatraPDF / Lector", "Ambos abren el mismo PDF de 5 páginas"), ("D", "IrfanView / Conversor", "5 de 6 formatos; WEBP no abrió en IrfanView"))], [2.4, 2.2, 2.2, 5], 17, .85)
texto(s, .6, 6, 12, .6, "Orden: original / réplica. Mediana de 3 ejecuciones, sin modelos de IA cargados.", 15, col=C(110, 110, 110))

s = lam("Conclusiones", "Cerrar con la idea principal y abrir preguntas. Preparar: ¿por qué no descompiló?, ¿qué es RAG?, ¿qué es zero-shot?, ¿qué hizo usted y qué hizo la IA?")
texto(s, .8, 1.6, 11.8, 5, ["**Observar bastó:** los formatos abiertos permiten reconstruir e interoperar sin descompilar.",
      "**Process Monitor** mostró diseño oculto: guardado atómico, candados y escrituras directas.",
      "**La IA aceleró el código, pero medir encontró sus errores.**", "**Datos limpios:** auditar etiquetas llevó el acierto de 82,2 % a 86,7 % (mismas clases).",
      "**IA local:** privada y sin internet, a cambio de memoria y precisión."], 24)
s = pr.slides.add_slide(pr.slide_layouts[6])
fl = s.background.fill
fl.solid()
fl.fore_color.rgb = V
texto(s, 1, 2.9, 11.3, 1.2, "Gracias. ¿Preguntas?", 46, True, B, PP_ALIGN.CENTER)
pr.save(R / "presentacion/Exposicion_Ingenieria_Inversa_DIAZ_ANCCO.pptx")
print(len(pr.slides), "láminas")
