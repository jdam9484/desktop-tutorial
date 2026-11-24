"""Genera el informe técnico en PDF. Las cifras se leen de evidencias/resultados."""
import json
import sys
from html import escape
from pathlib import Path

from PIL import Image as PI
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle as PS
from reportlab.lib.units import cm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (BaseDocTemplate, Frame, Image, KeepTogether, NextPageTemplate, PageBreak, PageTemplate,
                                Paragraph, Preformatted, Spacer, Table, TableStyle)
from reportlab.platypus.tableofcontents import TableOfContents

R = Path(__file__).resolve().parent.parent
E, F = R / "evidencias", R / "informe/fig"
REPO = sys.argv[1] if len(sys.argv) > 1 else "[enlace pendiente]"
W = "C:/Windows/Fonts/"
for n, f in (("T", "times.ttf"), ("TB", "timesbd.ttf"), ("TI", "timesi.ttf"), ("M", "consola.ttf")):
    pdfmetrics.registerFont(TTFont(n, W + f))
pdfmetrics.registerFontFamily("T", normal="T", bold="TB", italic="TI", boldItalic="TB")
V = colors.HexColor("#065f46")
P = PS("p", fontName="T", fontSize=11, leading=15, alignment=TA_JUSTIFY, spaceAfter=6)
L = PS("l", parent=P, leftIndent=14, bulletIndent=3, spaceAfter=3)
H1 = PS("h1", fontName="TB", fontSize=15, leading=19, textColor=V, spaceBefore=10, spaceAfter=7)
H2 = PS("h2", fontName="TB", fontSize=12.5, leading=16, spaceBefore=8, spaceAfter=5)
C = PS("c", fontName="TI", fontSize=9.5, leading=12, alignment=TA_CENTER, spaceBefore=3, spaceAfter=10)
TD = PS("td", fontName="T", fontSize=8.8, leading=11)
TH = PS("th", parent=TD, fontName="TB", textColor=colors.white)
PRE = PS("pre", fontName="M", fontSize=7.4, leading=9.2, backColor=colors.HexColor("#f5f5f5"), borderPadding=4,
         spaceAfter=8, spaceBefore=4)
ANCHO = A4[0] - 5 * cm
ia = json.load(open(E / "resultados/ia_final.json", encoding="utf8"))
cru = json.load(open(E / "resultados/ia_final_etiquetas_crudas.json", encoding="utf8"))
dev = json.load(open(E / "resultados/ia_desarrollo_inicial.json", encoding="utf8"))
cmp_ = json.load(open(E / "resultados/comparativa.json", encoding="utf8"))
pm = json.load(open(E / "procmon_resumen.json", encoding="utf8"))
rd = cmp_["rendimiento"]
pct = lambda x: f"{100 * x:.1f}".replace(".", ",") + " %"
num = lambda x: str(x).replace(".", ",")
S = []
nt, nf = [0], [0]


def p(t, st=P):
    S.append(Paragraph(t, st))


def lista(*xs):
    for x in xs:
        S.append(Paragraph(x, L, bulletText="•"))
    S.append(Spacer(1, 4))


def tabla(titulo, filas, anchos):
    nt[0] += 1
    t = Table([[Paragraph(escape(str(c)) if i else str(c), TH if i == 0 else TD) for c in f] if i == 0 else
               [Paragraph(str(c), TD) for c in f] for i, f in enumerate(filas)],
              colWidths=[ANCHO * a / sum(anchos) for a in anchos], repeatRows=1)
    t.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, 0), V), ("GRID", (0, 0), (-1, -1), .4, colors.grey),
                           ("VALIGN", (0, 0), (-1, -1), "TOP"), ("TOPPADDING", (0, 0), (-1, -1), 2.5),
                           ("BOTTOMPADDING", (0, 0), (-1, -1), 2.5),
                           ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f3f8f6")])]))
    S.append(Paragraph(f"<b>Tabla {nt[0]}.</b> {titulo}", C))
    S.append(t)
    S.append(Spacer(1, 9))


def img(ruta, w=ANCHO, hmax=10.5 * cm):
    a, b = PI.open(ruta).size
    k = min(w / a, hmax / b)
    return Image(str(ruta), a * k, b * k)


def fig(ruta, titulo, w=ANCHO, hmax=10.5 * cm):
    nf[0] += 1
    S.append(KeepTogether([img(ruta, w, hmax), Paragraph(f"<b>Figura {nf[0]}.</b> {titulo}", C)]))


def pre(t):
    S.append(Preformatted(t, PRE, maxLineLength=104, newLineChars=""))


class Doc(BaseDocTemplate):
    def afterFlowable(self, f):
        if isinstance(f, Paragraph) and f.style.name in ("h1", "h2"):
            niv = 0 if f.style.name == "h1" else 1
            k = f"s{self.seq.nextf('s')}"
            self.canv.bookmarkPage(k)
            self.canv.addOutlineEntry(f.getPlainText(), k, niv, niv > 0)
            self.notify("TOCEntry", (niv, f.getPlainText(), self.page, k))


def pie(c, d):
    c.saveState()
    c.setFont("T", 8.5)
    c.setFillColor(colors.grey)
    c.drawString(2.5 * cm, 1.3 * cm, "UNAMAD | Ingeniería de Sistemas e Informática | Inteligencia Artificial")
    c.drawRightString(A4[0] - 2.5 * cm, 1.3 * cm, f"{d.page}")
    c.restoreState()


# ------------------------------------------------------------------ 1. carátula
def cen(t, despues=15, fuente="T"):
    S.append(Paragraph(t, PS("car", fontName=fuente, fontSize=12, leading=20, alignment=TA_CENTER, spaceAfter=despues)))


S.append(Spacer(1, 1.6 * cm))
cen("“UNIVERSIDAD NACIONAL AMAZÓNICA DE MADRE DE DIOS”", 9, "TB")
cen("FACULTAD DE INGENIERÍA", 9)
cen("ESCUELA PROFESIONAL DE INGENIERÍA DE SISTEMAS E<br/>INFORMÁTICA", 6)
S.append(img(F / "escudo_unamad.png", 7.4 * cm, 7.4 * cm))
S.append(Spacer(1, 16))
cen("TRABAJO:", 5)
cen("“<i>Ingeniería Inversa Funcional y Reconstrucción Asistida por Inteligencia Artificial<br/>"
    "de Cuatro Programas de Escritorio</i>”", 9)
cen("ASIGNATURA:", 2)
cen("Inteligencia Artificial. Práctica N.º 7", 9)
cen("AUTOR:", 2)
cen("DIAZ ANCCO, Jorge Antonio.<br/>Código: 22221038", 9)
cen("DOCENTE:", 2)
cen("ALATRISTA AGUILAR, Miguel Ángel.", 40)
cen("Puerto Maldonado, 2026", 0)
S += [NextPageTemplate("n"), PageBreak()]
p("Contenido", PS("toc", fontName="TB", fontSize=15, leading=20, textColor=V))
toc = TableOfContents()
toc.levelStyles = [PS("t1", fontName="TB", fontSize=10.5, leading=15), PS("t2", fontName="T", fontSize=10, leading=13, leftIndent=16)]
S += [toc, PageBreak()]

# ------------------------------------------------------------------ 2. introducción
p("1. Introducción y selección del software", H1)
p("El enunciado pide hacer ingeniería inversa de cuatro programas de licencia u <i>open source</i> y exponer los resultados. "
  "La guía de laboratorio define cuatro categorías (A, B, C y D); se tomó un programa por categoría, dos comerciales o de "
  "licencia propietaria y dos de código abierto. De cada uno se dedujeron requisitos, interfaz y formato de archivo por "
  "observación, y se reconstruyó una réplica en Python con un módulo de inteligencia artificial que funciona de forma local.")
tabla("Programas seleccionados", [
    ["Op.", "Original (versión)", "Licencia", "Justificación técnica", "Réplica", "Módulo de IA"],
    ["A", "Apache OpenOffice Writer 4.1.17", "Open source, Apache 2.0", "Su formato ODT es un estándar abierto (ZIP + XML) fácil de auditar",
     "Escritor UNAMAD", "Corrector, resumen y autocompletado"],
    ["B", "Microsoft Paint 11.2609", "Comercial (incluido en Windows)", "Interfaz totalmente visible por UI Automation; PNG y BMP documentados",
     "Lienzo UNAMAD", "Quitar fondo y reconocer bocetos"],
    ["C", "SumatraPDF 3.6.1", "Open source, GPL-3.0", "Visor mínimo; configuración en texto legible", "Lector UNAMAD", "Chat con el PDF (RAG)"],
    ["D", "IrfanView 4.76", "Propietaria, gratuita para uso no comercial", "Menú Win32 clásico y línea de comandos que permite pruebas repetibles",
     "Conversor UNAMAD", "Clasificación de fauna y flora amazónica"]], [.5, 1.9, 1.6, 2.9, 1.4, 1.9])
p("<b>Alcance.</b> Las réplicas cubren las funciones esenciales de las Tablas 3 a 6, no la totalidad de cada programa. No se "
  "descompiló ningún binario ni se copiaron íconos, textos de ayuda o código: solo se observó comportamiento, interfaz, "
  "archivos producidos y accesos a disco, como exige la nota de ética de la guía.")
p(f"<b>Repositorio del proyecto:</b> <link href='{REPO}' color='#065f46'>{REPO}</link>")
p("<b>Entorno.</b> Windows 11, Intel Core i7-13650HX, 16 GB de RAM, NVIDIA RTX 5060 Laptop (8 GB), Python 3.12, PyQt6, "
  "Ollama 0.40 y ONNX Runtime.")

# ------------------------------------------------------------------ 3. evidencias
p("2. Evidencias de ingeniería inversa", H1)
p("2.1 Método y herramientas", H2)
lista("<b>Árbol de interfaz:</b> script propio con Microsoft UI Automation, la misma interfaz de programación que usan Inspect.exe y "
      "Accessibility Insights (<font name='M' size='9'>analisis/fase1_inspeccion.py</font>). El menú de IrfanView se leyó con GetMenu.",
      "<b>Accesos a disco:</b> Process Monitor 4.13, filtrando solo los cuatro procesos; la captura general se eliminó.",
      "<b>Cabeceras:</b> volcado hexadecimal (xxd), descompresión de ODT y ExifTool 13.64. El sitio de HxD respondía con error 502.",
      "<b>Archivos mínimos creados por los propios originales:</b> documento con una palabra en negrita (Writer, por su API UNO), "
      "imagen 10×10 de un color reescrita por Paint, y conversiones de IrfanView a cinco formatos.")
tabla("Datos de la inspección de caja negra", [
    ["Programa", "Clase de ventana", "Nodos UIA", "Elementos de menú Win32", "Eventos ProcMon", "Binarios cargados"]] + [
    [n, i["clase"], i["nodos_uia"], i["items_menu"] or "0 (menú propio)", f"{pm[k]['total']:,}".replace(",", " "), pm[k]["imagenes"]]
    for k, n in (("A_writer", "Writer"), ("B_paint", "Paint"), ("C_sumatra", "SumatraPDF"), ("D_irfanview", "IrfanView"))
    for i in [json.load(open(E / k / "info.json", encoding="utf8"))]], [1.2, 2, 1, 1.7, 1.3, 1.3])
p("<b>Limitación:</b> Writer y SumatraPDF dibujan sus menús sin exponer los submenús de forma completa, por lo que su "
  "inventario se basa en la barra superior, barras de herramientas, panel lateral y lo observado en pantalla.")

APPS = [
    ("A", "OpenOffice Writer", "A_writer", "Writer 4.1.17: menús, dos barras, regla, hoja, panel Propiedades y barra de estado",
     ["ODT, RTF, DOC, TXT, HTML", "Aplicar estilos, alinear, listar, contar", "ODT, PDF, RTF, HTML, TXT"],
     [("Abrir y guardar ODT", "Archivo, barra estándar; ZIP con mimetype", "odt.abrir / odt.guardar", "ida y vuelta; abre el mínimo"),
      ("Negrita, cursiva, subrayado", "Barra Formato: N C S", "negrita, cursiva, subrayado", "ida y vuelta"),
      ("Fuente y tamaño", "ComboBox «Fuente», «Tamaño de fuente»", "QFontComboBox, _tamano", "verificado en Writer"),
      ("Alineación", "4 botones «Alineado…»", "setAlignment", "ida y vuelta"),
      ("Viñetas y numeración", "SplitButton «Viñetas», «Numeración»", "lista", "ida y vuelta"),
      ("Estilos de párrafo", "ComboBox «Predeterminado»", "aplicar_estilo", "Writer ve «Heading 1»"),
      ("Buscar y reemplazar", "Cuadro «Buscar»", "buscar, reemplazar_todo", "test_reemplazar_todo"),
      ("Contador y página", "Barra de estado «Página 1/1»", "_contar", "visual"),
      ("Zoom", "Deslizador 100 %", "_zoom", "test_zoom_no_altera…"),
      ("Bloqueo del archivo", "ProcMon: .~lock.nombre#", "Candado", "test_candado")]),
    ("B", "Microsoft Paint", "B_paint", "Paint 11: cinta con grupos, lienzo de 1152×720, deslizadores de grosor y opacidad",
     ["PNG, JPG, BMP, GIF, TIFF, HEIC", "Trazos, formas, relleno, giros, recorte, escala", "PNG, JPG, BMP, GIF y otros"],
     [("Lápiz y pincel", "ToggleButton «Lápiz», id PencilTool", "Lienzo._trazar", "visual"),
      ("Borrador", "id EraserTool", "Lienzo._trazar (color 2)", "visual"),
      ("Relleno", "ToggleButton «Relleno»", "motor.rellenar", "test_relleno_respeta_bordes"),
      ("Formas", "Lista «Formas» (GridView)", "motor.trazo_forma (10)", "test_formas ×10"),
      ("Selector de colores", "ToggleButton «Selector de colores»", "Cuentagotas", "visual"),
      ("Recortar", "id CropButton", "recortar", "visual"),
      ("Girar y voltear", "id RotateDropdown, id Flip", "girar, voltear", "test_deshacer_rehacer"),
      ("Cambiar de tamaño", "Botón «Cambiar de tamaño y sesgar»", "redimensionar", "visual"),
      ("Deshacer y rehacer", "AppBarButton Ctrl+Z, Ctrl+Y", "deshacer, rehacer", "test_deshacer_rehacer"),
      ("Guardar", "Ctrl+S; %TEMP% y renombrado", "motor.guardar", "PNG, BMP, JPG, GIF")]),
    ("C", "SumatraPDF", "C_sumatra", "SumatraPDF 3.6.1: pestañas y una sola barra de herramientas",
     ["PDF, EPUB, XPS, CBZ…", "Renderizar, buscar, zoom, rotar", "Impresión, configuración por archivo"],
     [("Abrir", "Botón «Abrir (Ctrl + O)»", "Lector.abrir", "test_lector…"),
      ("Ir a página", "Edit «/ 5»", "Vista.ir", "test_lector…"),
      ("Página anterior y siguiente", "Botones (P) y (N)", "atajos P y N", "visual"),
      ("Ajustar al ancho o página", "Botones de ajuste", "Vista.ajustar", "test_lector…"),
      ("Rotar", "Ctrl+Shift+Subtract / +", "Vista.poner", "test_lector…"),
      ("Zoom", "Ctrl + / Ctrl -", "_zoom", "visual"),
      ("Buscar texto", "Edit «Buscar:», F3, Shift+F3", "Vista.buscar, siguiente", "3 apariciones de «Inspect»"),
      ("Coincidir mayúsculas", "CheckBox «Alternar coincidir…»", "filtro en buscar", "0 apariciones de «inspect»"),
      ("Pestañas", "SysTabControl32", "QTabWidget", "visual"),
      ("Recordar estado", "SumatraPDF-settings.txt: PageNo, Zoom, Rotation", "lector_config.json", "test_lector… (reabre en pág. 3 y 90°)")]),
    ("D", "IrfanView", "D_irfanview", "IrfanView 4.76: menú clásico de 265 elementos, barra de íconos y barra de estado",
     ["BMP, JPG, PNG, GIF, TIF, WEBP…", "Girar, voltear, escalar, efectos, lotes", "Los mismos formatos"],
     [("Abrir", "File › Open [O]", "Visor.abrir", "visual"),
      ("Identificar formato", "Image › Information [I]", "nucleo.cabecera", "5 cabeceras del original"),
      ("Guardar como", "File › Save as [S]", "nucleo.guardar", "test_convertir ×6"),
      ("Conversión por lotes", "File › Batch Conversion [B]", "nucleo.lote", "test_lote… ×2"),
      ("Girar", "Image › Rotate [L] [R]", "_img(rotate)", "visual"),
      ("Voltear", "Image › Flip [V] [H]", "_img(flip/mirror)", "visual"),
      ("Redimensionar", "Image › Resize [Ctrl+R]", "nucleo.redimensionar", "test_lote…"),
      ("Gris y negativo", "Ctrl+G, Ctrl+Shift+N", "_img", "visual"),
      ("Navegar la carpeta", "View › Next / Previous [Espacio, Retroceso]", "mover", "visual"),
      ("Zoom y ajuste", "View › Zoom [+] [-], [F]", "_zoom, ajustar", "visual")]),
]
BIN = {
    "A": ("El ODT es un contenedor ZIP de 17 entradas. La primera, <i>mimetype</i>, va <b>sin comprimir</b> (método <i>Stored</i>), así la "
          "firma del tipo queda legible en el desplazamiento 0x26. La negrita no está en el texto: es un estilo automático T1 al que el "
          "fragmento hace referencia. <i>meta.xml</i> guarda 1 párrafo, 3 palabras y 17 caracteres.",
          (E / "A_writer/odt_hex.txt").read_text().strip().split("\n")[:4],
          '<style:style style:name="T1" style:family="text">\n  <style:text-properties fo:font-weight="bold"/>\n</style:style>\n'
          '<text:p text:style-name="Standard">Hola <text:span text:style-name="T1">mundo</text:span>\n'
          '  <text:span text:style-name="T2"> UNAMAD</text:span></text:p>',
          "<b>Process Monitor:</b> Writer escribe <i>minimo_writer0.odt</i> y lo renombra sobre el destino (guardado atómico); crea el candado "
          "<i>.~lock.minimo_writer.odt#</i>; y guarda sus preferencias con el mismo patrón en <i>registrymodifications.xcu</i>."),
    "B": ("La entrada era un PNG RGB de 76 bytes (tipo de color 2). Al guardar, Paint produjo 537 bytes: cambió a <b>tipo 6 (RGBA)</b> y "
          "agregó los bloques sRGB, gAMA, pHYs (4724 píxeles por metro, 120 ppp) e iTXt con metadatos XMP.",
          ["Entrada:  0000 000d 4948 4452 0000 000a 0000 000a 0802 ....   IHDR 10x10, 8 bits, tipo 2 (RGB)",
           "Paint:    0000 000d 4948 4452 0000 000a 0000 000a 0806 ....   IHDR 10x10, 8 bits, tipo 6 (RGBA)",
           "          7352 4742 (sRGB)  6741 4d41 (gAMA)  7048 5973 0000 1274 (pHYs = 4724)  6954 5874 (iTXt)"], "",
          "<b>Process Monitor:</b> Paint escribe en <i>%TEMP%</i> y luego renombra hacia el destino. Entre los módulos cargados aparecen "
          "<i>AIServices.dll</i>, <i>PaintAIManager.dll</i> y <i>c2pa_c.dll</i> (por su nombre, servicios de IA y procedencia de contenido)."),
    "C": ("El PDF de prueba comienza con <i>%PDF-1.4</i> y cuatro bytes altos que lo marcan como binario; termina con la tabla <i>xref</i>, el "
          "<i>trailer</i> (488 objetos) y <i>startxref</i>. Por eso un visor lee el archivo <b>desde el final</b>.",
          (E / "C_sumatra/pdf_hex.txt").read_text(errors="replace").strip().split("\n")[:2] +
          ["trailer <</Size 488 /Root 33 0 R /Info 1 0 R>>", "startxref 215233", "%%EOF"], "",
          "<b>Process Monitor:</b> una única escritura, <i>SumatraPDF-settings.txt</i>; el PDF solo se lee. Los binarios propios "
          "son dos: <i>SumatraPDF.exe</i> y <i>libmupdf.dll</i>, de modo que el renderizado lo hace MuPDF."),
    "D": ("IrfanView reconoce el formato por su número mágico. Los mínimos de 10×10 muestran: BMP de 24 bits con píxeles en orden BGR y "
          "filas rellenadas a múltiplo de 4; JPEG con JFIF y submuestreo 4:2:0; TIFF en orden Intel sin compresión.",
          ["BMP  42 4d 76 01 00 00 ...  'BM', 374 bytes, desplazamiento 54, 24 bpp", "JPG  ff d8 ff e0 00 10 4a 46 49 46  SOI + APP0 'JFIF'",
           "GIF  47 49 46 38 39 61 0a 00 0a 00  'GIF89a' 10x10", "TIF  49 49 2a 00 34 01 00 00  'II', 42, IFD en 0x134",
           "PNG  89 50 4e 47 0d 0a 1a 0a  IHDR 10x10 tipo 2"], "",
          "<b>Process Monitor:</b> escribe <b>directo sobre el destino</b>, sin temporal (un corte dejaría el archivo a medias), y lee "
          "<i>i_view64.ini</i> cientos de veces (464 lecturas en la sesión)."),
}
for i, (op, nom, k, cap, io, mat) in enumerate(APPS, 2):
    S.append(PageBreak())
    p(f"2.{i} Opción {op}: {nom}", H2)
    fig(E / k / "ventana_original.png", cap, hmax=8 * cm if op != "D" else 4.2 * cm)
    p(f"<b>Entradas:</b> {io[0]}. <b>Procesos:</b> {io[1]}. <b>Salidas:</b> {io[2]}.")
    fig(F / f"arbol_{op}.png", f"Extracto literal del árbol UI Automation de {nom} (completo en evidencias/{k}/arbol_uia.txt)", hmax=7.5 * cm)
    tabla(f"Matriz de trazabilidad funcional: {nom}", [["#", "Función", "Evidencia en el original", "Implementación", "Verificación"]] +
          [[j, *f] for j, f in enumerate(mat, 1)], [.5, 2, 3, 2.3, 2.2])
    d = BIN[op]
    p("<b>Análisis del archivo.</b> " + d[0])
    pre("\n".join(d[1]))
    if d[2]:
        pre(d[2])
    p(d[3])
    S.append(KeepTogether([Table([[img(F / f"casos_{op}.png", ANCHO * .38), img(F / f"flujo_{op}.png", ANCHO * .6)]])]))
    nf[0] += 1
    p(f"<b>Figura {nf[0]}.</b> Casos de uso y flujo funcional deducido (opción {op})", C)

# ------------------------------------------------------------------ 4. prompts
S.append(PageBreak())
p("3. Ingeniería de prompts aplicada", H1)
p("<b>Cómo se trabajó.</b> Se usó Claude (modelo Opus 5.5, en la herramienta Claude Code). El estudiante dio el encargo, los datos y las "
  "decisiones; el asistente ejecutó la inspección, redactó las especificaciones estructuradas a partir de los hallazgos, generó el "
  "código y las pruebas, y ayudó a redactar este informe. El encargo inicial fue, textualmente:")
pre("ayudame con esto, deje en la carpeta un archivo pdf y el enunciado es este Enunciado de la tarea:\nAL ALUMNO DEBERA HACER ING INVERSA DE 04 "
    "SOFTWARE DE LICENCIA O OPEN SOURCE Y EXPONER EN CLASE LOS\nRESULTADOS. TIENES PERSIMO TOTAL DE CUALQUIER APLICACION QUE NECESITES")
p("Después se aplicó la descomposición en tres iteraciones por programa (interfaz, lógica e IA). Registro textual:")
for f, t in (("A_escritor", "3.1 Prompts de la opción A"), ("B_lienzo", "3.2 Prompts de la opción B"),
             ("C_lector", "3.3 Prompts de la opción C"), ("D_conversor", "3.4 Prompts de la opción D")):
    p(t, H2)
    for bloque in (R / f"prompts/{f}.md").read_text(encoding="utf8").split("\n## ")[1:]:
        pre(bloque.strip().replace("²", "2"))
p("3.5 Errores del modelo y depuración", H2)
tabla("Errores encontrados en el código o diseño generado, causa y corrección", [
    ["Síntoma", "Causa", "Corrección", "Efecto medido"],
    ["El zoom cambiaba la fuente guardada en el ODT", "La fuente base se fijó en el documento y no en el editor; el zoom la recalculaba", "Fijar la fuente en el editor y volver a 100 % antes de guardar", "Prueba en verde"],
    ["DOCX abierto a 11 pt en Writer", "No se escribía la fuente base en el estilo Normal", "Definir Normal y Heading 1 a 3", "12 y 20 pt verificados en Writer"],
    ["El RAG respondía otra fila de la tabla", "El texto plano del PDF pierde la relación fila-columna", "Un fragmento por fila con «columna: valor»", "Responde bien la opción C"],
    [f"RAG lento: {num(round(dev['rag']['s_mediana'], 1))} s por pregunta", "bge-m3 y Llama 3.1 se turnaban la VRAM de 8 GB; contexto de 8192", "Embeddings en CPU y contexto de 4096", f"{num(round(ia['rag']['s_mediana'], 1))} s"],
    ["Clasificador: tucán y caimán con 0 aciertos", "CLIP cuantizado a 8 bits degrada los vectores", "Usar fp32 con las mismas etiquetas", "60,0 % a 82,2 % en desarrollo"],
    ["Réplicas con 660 MB de memoria", "OpenBLAS reserva memoria por cada hilo", "OPENBLAS_NUM_THREADS=1", "48 a 50 MB"],
    ["Posible pérdida de texto al corregir", "Una respuesta truncada reemplazaría texto completo", "Límite de 600 palabras y vista previa", "Preventivo"],
    ["Fotos de prueba con etiqueta falsa", "La búsqueda por nombre «Ara» devolvía otros seres vivos", "Auditoría por taxonomía; 7 fotos sustituidas", "n = 95 verificadas"]], [2, 2.6, 2.4, 1.6])

# ------------------------------------------------------------------ 5. arquitectura
p("4. Arquitectura del prototipo e integración de IA", H1)
fig(F / "componentes.png", "Diagrama de componentes. Los cuatro programas usan también el guardado atómico de comun/archivos.py "
    "(las flechas de ese módulo se omiten por claridad)", hmax=8.5 * cm)
p("<b>Acoplamiento asíncrono.</b> La clase <i>Tarea</i> hereda de QThread. Ejecuta una función en otro hilo y se comunica con tres "
  "señales: avance (trozos de texto o progreso), lista (resultado) y fallo (mensaje legible). Los controles se leen antes de lanzar el "
  "hilo y nunca se tocan desde él. Una prueba automática verifica que, con una tarea de 1 s en curso, la interfaz nunca quede más de "
  "300 ms sin atender eventos. Todas las tareas de texto, RAG y lotes pueden cancelarse.")
p("4.1 Escritor: modelo de lenguaje local", H2)
p("Corregir y resumir usan llama3.1:8b por la API de Ollama con respuesta en flujo; autocompletar usa llama3.2:3b, más rápido. La propuesta "
  "se muestra en gris y se acepta con Tab; la corrección se revisa antes de reemplazar.")
fig(E / "A_writer/replica_ia.png", "Escritor UNAMAD: corrección propuesta por la IA antes de reemplazar", hmax=8.3 * cm)
p("4.2 Lienzo: segmentación y reconocimiento de bocetos", H2)
p("U²-Net recibe la imagen a 320×320, predice un mapa de prominencia que se normaliza, se reescala y se usa como canal alfa. Para los bocetos, "
  "CLIP compara el vector de la imagen con el de 24 etiquetas («a hand-drawn sketch of a …») y devuelve las probabilidades.")
nf[0] += 1
S.append(Table([[img(E / "B_paint/replica_fondo.png", ANCHO * .49), img(E / "B_paint/replica_boceto.png", ANCHO * .49)]]))
p(f"<b>Figura {nf[0]}.</b> Lienzo UNAMAD: fondo eliminado (izq.) y boceto reconocido como gato (der.)", C)
p("4.3 Lector: RAG con citas", H2)
p("El texto se extrae en un proceso aparte, se divide en ventanas de 170 palabras con 40 de solape sin cruzar páginas, y cada fila de tabla es un "
  "fragmento propio. Los vectores bge-m3 se guardan en caché; se recuperan los 5 más parecidos por coseno y Llama 3.1 responde solo con "
  "ese contexto, citando la página. La cita es un enlace que lleva a la página.")
fig(E / "C_sumatra/replica_rag.png", "Lector UNAMAD: dos respuestas con cita y una negativa correcta", hmax=9 * cm)
p("4.4 Conversor: clasificación de fauna y flora", H2)
p("Clasificación <i>zero-shot</i> con CLIP ViT-B/32: 22 etiquetas en español asociadas a descripciones en inglés, promedio de 3 plantillas y umbral "
  "de 0,40. En el lote, cada imagen va a la subcarpeta de su especie y se escribe <i>clasificacion.csv</i>.")
nf[0] += 1
S.append(Table([[img(E / "D_irfanview/replica_especie.png", ANCHO * .55), img(E / "D_irfanview/replica_lote.png", ANCHO * .43)]]))
p(f"<b>Figura {nf[0]}.</b> Conversor UNAMAD: especie identificada y lote clasificado", C)
p("4.5 Precisión y latencia de la IA", H2)
f, b, r, c = ia["fauna"], ia["bocetos"], ia["rag"], ia["corrector"]
tabla("Evaluación con datos distintos de los usados para ajustar", [
    ["Módulo", "Datos", "Resultado", "Latencia (mediana)"],
    ["Fauna y flora (CLIP)", f"{f['n']} fotos CC de iNaturalist, 19 clases", f"Acierto {pct(f['top1'])}; entre las 3 primeras {pct(f['top3'])}", f"{f['ms']:.0f} ms"],
    ["Bocetos (CLIP)", f"{b['n']} dibujos de Quick, Draw!, 23 clases", f"Acierto {pct(b['top1'])}; entre las 3 primeras {pct(b['top3'])}", f"{b['ms']:.0f} ms"],
    ["RAG", f"{r['n']} preguntas (3 sin respuesta en el PDF)", f"{r['aciertos']}/{r['n']} correctas; {r['citas_ok']}/{r['con_cita']} citas correctas; 3/3 negativas correctas", f"{num(round(r['s_mediana'], 1))} s (indexar: {num(round(r['indexar_s'], 1))} s)"],
    ["Corrector", "8 frases, 14 correcciones esperadas", f"{c['corregidos']}/{c['total']}", f"{num(round(c['s_mediana'], 2))} s"],
    ["Autocompletar", "3 frases", "Coherente (sin métrica)", f"{num(round(ia['autocompletar']['s_siguientes'], 2))} s (primera: {num(round(ia['autocompletar']['s_primera'], 1))} s)"],
    ["Quitar fondo", f"{ia['fondo']['n']} fotos", "Sin máscara de referencia: solo evaluación visual", f"{num(round(ia['fondo']['s_mediana'], 2))} s (primera: {num(round(ia['fondo']['s_primera'], 1))} s)"]], [1.5, 2.3, 3, 1.9])
p(f"<b>Lectura crítica.</b> (1) La fauna daba {pct(cru['fauna']['top1'])} sobre 90 fotos antes de auditar las etiquetas; 7 fotos no eran del taxón "
  "pedido (por ejemplo, un abedul como «guacamayo») y se sustituyeron con un criterio que no mira las predicciones; además se agregó la clase "
  f"«rana». (2) Los errores de fauna se concentran en nenúfar gigante y oso hormiguero (60 % cada uno). (3) En bocetos falla mariposa (20 %) y reloj (40 %). "
  "(4) El RAG falló al confundir la sección 6 del informe con la sección 6 de la guía: hay dos numeraciones. (5) El corrector cambió el "
  "sentido en algunas frases («Mas sin embargo no lo iso» pasó a «Sin embargo, no lo hago») y varía entre ejecuciones (10 y 11 de 14), "
  "por lo que la vista previa es necesaria. Las muestras son pequeñas: las cifras son orientativas.")

# ------------------------------------------------------------------ 6. comparativo
p("5. Cuadro comparativo: original frente a réplica con IA", H1)
v = lambda k, x: num(rd[k][x])
tabla("Consumo y arranque (mediana de 3 ejecuciones, sin modelos de IA cargados)", [
    ["Programa", "Arranque original", "Arranque réplica", "Memoria original", "Memoria réplica"]] + [
    [n, v(o + "_original", "arranque_s") + " s", v(o + "_replica", "arranque_s") + " s", v(o + "_original", "privada_mb") + " MB", v(o + "_replica", "privada_mb") + " MB"]
    for o, n in (("A", "Writer / Escritor"), ("B", "Paint / Lienzo"), ("C", "SumatraPDF / Lector"), ("D", "IrfanView / Conversor"))], [2, 1.4, 1.4, 1.4, 1.4])
p("Memoria privada del proceso principal. Con CLIP cargado el proceso sube a unos 690 MB y con U²-Net además a unos 1 400 MB; los modelos se cargan "
  "solo al usar la función. Writer tardó 5,4 s en su primer arranque. Los originales en código nativo (SumatraPDF, IrfanView) ganan con claridad "
  "en arranque y memoria. Lienzo consume menos que Paint, pero también ofrece menos funciones.")
fd = cmp_["D_fidelidad"]
lt = cmp_["D_lote40_png_s"]
tabla("Compatibilidad, tiempos y capacidades", [
    ["Aspecto", "A. Writer / Escritor", "B. Paint / Lienzo", "C. SumatraPDF / Lector", "D. IrfanView / Conversor"],
    ["Original abre lo de la réplica", "ODT y DOCX abren sin error; Writer reconoce título, negrita, cursiva, subrayado, tamaños, centrado y listas", "PNG, BMP y JPG abren; Paint informa 37 × 23 píxeles, el tamaño exacto", "No aplica: es un visor y no genera PDF", "BMP, JPG, PNG, GIF y TIF: dimensiones correctas. WEBP no respondió en 20 s (instalación sin complementos)"],
    ["Réplica abre lo del original", "Sí: texto y negrita exactos", "Sí", "Mismo PDF, 5 páginas", "Sí: 5 de 5 cabeceras"],
    ["Fidelidad o tiempo", "Ida y vuelta sin pérdida en las funciones probadas", "PNG tipo 6 y pHYs como Paint", "Búsqueda con y sin mayúsculas", f"Misma foto: {num(fd['png']['psnr'])} dB en PNG, {num(fd['jpg']['psnr'])} dB en JPG. 40 imágenes: {num(lt['replica'])} s frente a {num(lt['irfan_proceso_por_archivo'])} s (IrfanView lanzado una vez por archivo, lo que lo perjudica)"],
    ["Seguridad de guardado", "Ambos atómicos", "Ambos atómicos", "No modifica el PDF", "Réplica atómica; original directo"],
    ["Nueva capacidad cognitiva", "Corregir, resumir, autocompletar", "Reconocer bocetos; quitar fondo local (Paint ya trae una función propia)", "Preguntar al PDF con citas", "Clasificar y ordenar por especie"],
    ["Lo que la réplica no tiene", "Tablas, imágenes, encabezados, notas", "Capas, texto editable, Copilot", "Anotaciones, formularios", "Complementos, TWAIN, 8BF, cientos de formatos"]], [1.2, 2, 1.8, 1.7, 2.3])
p("<b>Pruebas automáticas.</b> 52 pruebas (<font name='M' size='9'>pytest tests</font>), todas correctas: formatos, guardado atómico, formas, "
  "búsqueda, cabeceras, lotes con archivos dañados, Ollama apagado e interfaz sin bloqueo.")

# ------------------------------------------------------------------ 7. conclusiones
p("6. Conclusiones y recomendaciones", H1)
lista("La observación bastó para reconstruir funciones interoperables: Writer y Paint abrieron los archivos de las réplicas, porque los formatos ODT, PNG y BMP son "
      "estándares abiertos. No hizo falta descompilar.",
      "Process Monitor reveló decisiones de diseño que no se ven en la interfaz: guardado atómico y candado en Writer, temporal en Paint, escritura directa en IrfanView.",
      "La IA generativa aceleró la reconstrucción, pero su primer código tuvo errores que solo aparecieron al medir: cuantización, memoria, VRAM, tablas y fuentes. "
      "El valor estuvo en las pruebas contra el original.",
      "Separar datos de ajuste y de prueba, y auditar etiquetas, cambió las cifras de forma apreciable (82,2 % a 86,7 % en fauna con las mismas clases; 87,4 % al sumar «rana»). Sin esa revisión el informe habría sido inexacto.",
      "La IA local protege la privacidad y funciona sin internet, a cambio de memoria y de modelos menos precisos que los comerciales.")
p("<b>Recomendaciones:</b> entrenar un clasificador con fotos propias de Madre de Dios; añadir OCR al Lector para PDF escaneados; medir la eliminación de fondo con "
  "máscaras de referencia; y mantener siempre la revisión humana de los textos corregidos.")
p("Referencias", H1)
for x in ("OASIS. <i>Open Document Format for Office Applications (OpenDocument) v1.2</i>, 2011.",
          "W3C. <i>Portable Network Graphics (PNG) Specification</i>.", "ISO 32000-1:2008. <i>Document management: Portable document format</i>.",
          "Radford, A. et al. <i>Learning Transferable Visual Models From Natural Language Supervision</i> (CLIP). ICML, 2021.",
          "Qin, X. et al. <i>U²-Net: Going Deeper with Nested U-Structure for Salient Object Detection</i>. Pattern Recognition, 2020.",
          "Lewis, P. et al. <i>Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks</i>. NeurIPS, 2020.",
          "Chen, J. et al. <i>BGE M3-Embedding</i>. 2024.", "Microsoft. <i>UI Automation</i> y <i>Process Monitor</i> (documentación).",
          "iNaturalist (fotos CC0 y CC BY; créditos en evaluacion/creditos_fotos_test.csv). Google. <i>Quick, Draw! Dataset</i>, CC BY 4.0."):
    p(x, L)

d = Doc(str(R / "informe/Informe_Ingenieria_Inversa_DIAZ_ANCCO.pdf"), pagesize=A4, title="Ingeniería inversa de cuatro programas",
        author="Jorge Antonio Diaz Ancco", lang="es")
fr = Frame(2.5 * cm, 2 * cm, ANCHO, A4[1] - 4.2 * cm, id="f", leftPadding=0, rightPadding=0)
d.addPageTemplates([PageTemplate("c", fr), PageTemplate("n", fr, onPage=pie)])
d.multiBuild(S)
print("páginas:", d.page)
