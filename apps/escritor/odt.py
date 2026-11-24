"""Lectura y escritura de ODT <-> QTextDocument según la estructura observada en OpenOffice Writer."""
import re
import zipfile
from datetime import datetime

from lxml import etree
from PyQt6.QtCore import Qt
from PyQt6.QtGui import (QColor, QFont, QTextBlockFormat, QTextCharFormat, QTextCursor, QTextDocument,
                         QTextListFormat)

from apps.comun.archivos import guardar_atomico

MIME = "application/vnd.oasis.opendocument.text"
NS = {p: "urn:oasis:names:tc:opendocument:xmlns:" + u for p, u in dict(
    office="office:1.0", style="style:1.0", text="text:1.0", table="table:1.0",
    fo="xsl-fo-compatible:1.0", meta="meta:1.0", manifest="manifest:1.0").items()}
NS["dc"] = "http://purl.org/dc/elements/1.1/"
TAM_TITULO = {1: 20, 2: 16, 3: 14}
ALIN = {"start": Qt.AlignmentFlag.AlignLeft, "left": Qt.AlignmentFlag.AlignLeft,
        "end": Qt.AlignmentFlag.AlignRight, "right": Qt.AlignmentFlag.AlignRight,
        "center": Qt.AlignmentFlag.AlignHCenter, "justify": Qt.AlignmentFlag.AlignJustify}


def q(nombre):
    p, n = nombre.split(":")
    return f"{{{NS[p]}}}{n}"


def _e(padre, nombre, **at):
    """Crea un elemento; los atributos usan '__' en vez de ':' y '_' en vez de '-'."""
    el = etree.SubElement(padre, q(nombre))
    for k, v in at.items():
        p, n = k.split("__")
        el.set(q(p + ":" + n.replace("_", "-")), str(v))
    return el


# ---------------------------------------------------------------- escritura
def _props(fmt, base):
    """Propiedades fo:/style: de un fragmento (solo lo que difiere de lo normal)."""
    d = {}
    if fmt.fontWeight() >= QFont.Weight.Bold:
        d["fo:font-weight"] = "bold"
    if fmt.fontItalic():
        d["fo:font-style"] = "italic"
    if fmt.fontUnderline():
        d["style:text-underline-style"] = "solid"
    if fmt.fontStrikeOut():
        d["style:text-line-through-style"] = "solid"
    fams = fmt.fontFamilies()
    if fams and fams[0] != base.family():
        d["style:font-name"] = fams[0]
    if fmt.fontPointSize() > 0 and fmt.fontPointSize() != base.pointSizeF():
        d["fo:font-size"] = f"{fmt.fontPointSize():g}pt"
    if fmt.foreground().style() != Qt.BrushStyle.NoBrush:
        d["fo:color"] = fmt.foreground().color().name()
    if fmt.background().style() != Qt.BrushStyle.NoBrush:
        d["fo:background-color"] = fmt.background().color().name()
    return d


def _texto(padre, s):
    """Agrega texto respetando tabuladores, saltos y espacios múltiples (text:s)."""
    ult = None

    def poner(t):
        if ult is None:
            padre.text = (padre.text or "") + t
        else:
            ult.tail = (ult.tail or "") + t
    inicio = padre.text is None and len(padre) == 0
    for tr in re.findall(r"\t|[ \n]| {2,}|^ |[^\t \n ]+(?: [^\t \n ]+)*| ", s):
        if tr == "\t":
            ult = _e(padre, "text:tab")
        elif tr in " \n":
            ult = _e(padre, "text:line-break")
        elif tr.isspace() and (len(tr) > 1 or inicio):
            ult = _e(padre, "text:s", text__c=len(tr))
        else:
            poner(tr)
        inicio = False


def _xml(raiz):
    return etree.tostring(raiz, xml_declaration=True, encoding="UTF-8")


def guardar(doc: QTextDocument, ruta):
    base = doc.defaultFont()
    cont = etree.Element(q("office:document-content"), nsmap=NS)
    cont.set(q("office:version"), "1.2")
    fuentes = _e(cont, "office:font-face-decls")
    autos = _e(cont, "office:automatic-styles")
    cuerpo = _e(_e(cont, "office:body"), "office:text")
    est_t, est_p, fams = {}, {}, {base.family()}

    def estilo_t(d):
        if not d:
            return None
        k = tuple(sorted(d.items()))
        if k not in est_t:
            est_t[k] = f"T{len(est_t) + 1}"
            p = _e(_e(autos, "style:style", style__name=est_t[k], style__family="text"), "style:text-properties")
            for a, v in d.items():
                p.set(q(a), v)
            if "style:font-name" in d:
                fams.add(d["style:font-name"])
        return est_t[k]

    def estilo_p(al, padre):
        if al in ("start", ""):
            return padre
        k = (al, padre)
        if k not in est_p:
            est_p[k] = f"P{len(est_p) + 1}"
            s = _e(autos, "style:style", style__name=est_p[k], style__family="paragraph",
                   style__parent_style_name=padre)
            _e(s, "style:paragraph-properties", fo__text_align=al)
        return est_p[k]

    for n in ("LV", "LN"):
        ls = _e(autos, "text:list-style", style__name=n)
        if n == "LV":
            niv = _e(ls, "text:list-level-style-bullet", text__level=1)
            niv.set(q("text:bullet-char"), "•")
        else:
            niv = _e(ls, "text:list-level-style-number", text__level=1, style__num_suffix=".")
            niv.set(q("style:num-format"), "1")
        _e(niv, "style:list-level-properties", text__space_before="0.6cm", text__min_label_width="0.6cm")

    b, lista_qt, lista_x = doc.begin(), None, None
    while b.isValid():
        f = b.blockFormat()
        al = next((k for k, v in ALIN.items() if f.alignment() & v and k not in ("left", "right")), "start")
        nivel = f.headingLevel()
        padre = cuerpo
        if b.textList():
            if lista_x is None or b.textList().objectIndex() != lista_qt:
                num = b.textList().format().style() == QTextListFormat.Style.ListDecimal
                lista_x = _e(cuerpo, "text:list", text__style_name="LN" if num else "LV")
                lista_qt = b.textList().objectIndex()
            padre = _e(lista_x, "text:list-item")
        else:
            lista_x = lista_qt = None
        if nivel:
            p = _e(padre, "text:h", text__style_name=estilo_p(al, f"Heading_20_{nivel}"), text__outline_level=nivel)
        else:
            p = _e(padre, "text:p", text__style_name=estilo_p(al, "Standard"))
        it = b.begin()
        while not it.atEnd():
            fr = it.fragment()
            d = _props(fr.charFormat(), base)
            if nivel:  # el estilo de título ya aporta tamaño y negrita
                if d.get("fo:font-size") == f"{TAM_TITULO.get(nivel, 14):g}pt":
                    d.pop("fo:font-size")
                d.pop("fo:font-weight", None)
            n = estilo_t(d)
            destino = _e(p, "text:span", text__style_name=n) if n else (
                p if len(p) == 0 else _e(p, "text:span"))
            _texto(destino, fr.text())
            it += 1
        b = b.next()
    for fam in sorted(fams):
        el = _e(fuentes, "style:font-face", style__name=fam)
        el.set("{urn:oasis:names:tc:opendocument:xmlns:svg-compatible:1.0}font-family", f"'{fam}'")

    est = etree.Element(q("office:document-styles"), nsmap=NS)
    est.set(q("office:version"), "1.2")
    s = _e(est, "office:styles")
    d = _e(_e(s, "style:style", style__name="Standard", style__family="paragraph"), "style:text-properties",
           fo__font_size=f"{base.pointSizeF():g}pt")
    d.set(q("fo:font-family"), f"'{base.family()}'")
    for i, t in TAM_TITULO.items():
        h = _e(s, "style:style", style__name=f"Heading_20_{i}", style__display_name=f"Heading {i}",
               style__family="paragraph", style__parent_style_name="Standard", style__default_outline_level=i)
        _e(h, "style:text-properties", fo__font_size=f"{t}pt", fo__font_weight="bold")
    au = _e(est, "office:automatic-styles")
    _e(_e(au, "style:page-layout", style__name="pm1"), "style:page-layout-properties",
       fo__page_width="21cm", fo__page_height="29.7cm", fo__margin="2cm")
    _e(_e(est, "office:master-styles"), "style:master-page", style__name="Standard", style__page_layout_name="pm1")

    plano = doc.toPlainText()
    met = etree.Element(q("office:document-meta"), nsmap=NS)
    met.set(q("office:version"), "1.2")
    om = _e(met, "office:meta")
    _e(om, "meta:generator").text = "EscritorUNAMAD/1.0"
    _e(om, "dc:date").text = datetime.now().isoformat(timespec="seconds")
    _e(om, "meta:document-statistic", meta__paragraph_count=doc.blockCount(),
       meta__word_count=len(plano.split()), meta__character_count=len(plano.replace("\n", "")))
    man = etree.Element(q("manifest:manifest"), nsmap={"manifest": NS["manifest"]})
    man.set(q("manifest:version"), "1.2")
    for pth, mt in (("/", MIME), ("content.xml", "text/xml"), ("styles.xml", "text/xml"), ("meta.xml", "text/xml")):
        _e(man, "manifest:file-entry", manifest__full_path=pth, manifest__media_type=mt)

    def escribir(tmp):
        with zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED) as z:
            z.writestr("mimetype", MIME, zipfile.ZIP_STORED)  # primera entrada y sin comprimir
            z.writestr("content.xml", _xml(cont))
            z.writestr("styles.xml", _xml(est))
            z.writestr("meta.xml", _xml(met))
            z.writestr("META-INF/manifest.xml", _xml(man))
    guardar_atomico(ruta, escribir)


# ---------------------------------------------------------------- lectura
def abrir(ruta, doc: QTextDocument):
    with zipfile.ZipFile(ruta) as z:
        if z.read("mimetype").decode().strip() != MIME:
            raise ValueError("El archivo no es un documento de texto ODT.")
        seguro = etree.XMLParser(resolve_entities=False, no_network=True)
        cont = etree.fromstring(z.read("content.xml"), seguro)
        raices = [cont] + ([etree.fromstring(z.read("styles.xml"), seguro)] if "styles.xml" in z.namelist() else [])
    estilos, listas = {}, {}
    for r in reversed(raices):
        for s in r.iter(q("style:style")):
            d = {"padre": s.get(q("style:parent-style-name"))}
            for hijo in s:
                if hijo.tag in (q("style:text-properties"), q("style:paragraph-properties")):
                    d.update(hijo.attrib)
            estilos[(s.get(q("style:family")), s.get(q("style:name")))] = d
        for ls in r.iter(q("text:list-style")):
            listas[ls.get(q("style:name"))] = ls.find(q("text:list-level-style-number")) is not None

    def resolver(fam, nombre, prof=0):
        d = estilos.get((fam, nombre))
        if d is None or prof > 20:
            return {}
        r = resolver(fam, d["padre"], prof + 1) if d["padre"] else {}
        return {**r, **{k: v for k, v in d.items() if k != "padre"}}

    def formato(props, titulo=0):
        f = QTextCharFormat()
        g = lambda k: props.get(q(k))
        if g("fo:font-weight") in ("bold", "600", "700", "800", "900") or titulo:
            f.setFontWeight(QFont.Weight.Bold)
        if g("fo:font-style") in ("italic", "oblique"):
            f.setFontItalic(True)
        if g("style:text-underline-style") not in (None, "none"):
            f.setFontUnderline(True)
        if g("style:text-line-through-style") not in (None, "none"):
            f.setFontStrikeOut(True)
        fam = g("style:font-name") or g("fo:font-family")
        if fam:
            f.setFontFamilies([fam.strip("'")])
        t = g("fo:font-size")
        if t and t.endswith("pt"):
            f.setFontPointSize(float(t[:-2]))
        elif titulo:
            f.setFontPointSize(TAM_TITULO.get(titulo, 13))
        if (g("fo:color") or "").startswith("#"):
            f.setForeground(QColor(g("fo:color")))
        if (g("fo:background-color") or "").startswith("#"):
            f.setBackground(QColor(g("fo:background-color")))
        return f

    doc.clear()
    cur = QTextCursor(doc)
    primero = [True]

    def inline(el, props, titulo):
        if el.text:
            cur.insertText(re.sub(r"\s+", " ", el.text), formato(props, titulo))
        for h in el:
            if h.tag == q("text:span"):
                inline(h, {**props, **resolver("text", h.get(q("text:style-name")))}, titulo)
            elif h.tag == q("text:s"):
                cur.insertText(" " * int(h.get(q("text:c"), "1")), formato(props, titulo))
            elif h.tag == q("text:tab"):
                cur.insertText("\t", formato(props, titulo))
            elif h.tag == q("text:line-break"):
                cur.insertText(" ", formato(props, titulo))
            elif h.tag == q("text:a"):
                inline(h, props, titulo)
            if h.tail:
                cur.insertText(re.sub(r"\s+", " ", h.tail), formato(props, titulo))

    def parrafo(el, lista=None):
        nivel = int(el.get(q("text:outline-level"), "1")) if el.tag == q("text:h") else 0
        props = resolver("paragraph", el.get(q("text:style-name")))
        bf = QTextBlockFormat()
        bf.setAlignment(ALIN.get(props.get(q("fo:text-align")), Qt.AlignmentFlag.AlignLeft))
        if nivel:
            bf.setHeadingLevel(min(nivel, 6))
        if primero[0]:
            cur.setBlockFormat(bf)
            primero[0] = False
        else:
            cur.insertBlock(bf, QTextCharFormat())
        solo_texto = {k: v for k, v in props.items() if k != q("fo:background-color")}
        inline(el, solo_texto, nivel)
        if lista is not None:
            if lista["qt"] is None:
                lf = QTextListFormat()
                lf.setStyle(QTextListFormat.Style.ListDecimal if lista["num"] else QTextListFormat.Style.ListDisc)
                lista["qt"] = cur.createList(lf)
            else:
                lista["qt"].add(cur.block())
        elif cur.block().textList():
            cur.block().textList().remove(cur.block())

    def recorrer(el, lista=None):
        for h in el:
            if h.tag in (q("text:p"), q("text:h")):
                parrafo(h, lista)
            elif h.tag == q("text:list"):
                recorrer(h, {"qt": None, "num": listas.get(h.get(q("text:style-name")), False)})
            elif h.tag in (q("text:list-item"), q("text:section"), q("table:table"), q("table:table-row"),
                           q("table:table-cell"), q("table:table-header-rows")):
                recorrer(h, lista)
    recorrer(cont.find(".//" + q("office:text")))
    doc.setModified(False)
