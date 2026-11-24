"""Apertura y guardado por extensión, y candado de edición (.~lock.nombre#) como el observado en Writer."""
import getpass
import os
import socket
from datetime import datetime
from pathlib import Path

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont, QTextBlockFormat, QTextCharFormat, QTextCursor

from apps.comun.archivos import guardar_atomico
from . import odt

FILTRO = "Documentos (*.odt *.docx *.html *.txt);;ODT (*.odt);;Word (*.docx);;HTML (*.html);;Texto (*.txt)"


def abrir(ruta, doc):
    ext = Path(ruta).suffix.lower()
    if ext == ".odt":
        odt.abrir(ruta, doc)
    elif ext == ".docx":
        _abrir_docx(ruta, doc)
    elif ext in (".html", ".htm"):
        doc.setHtml(Path(ruta).read_text(encoding="utf-8", errors="replace"))
    else:
        datos = Path(ruta).read_bytes()
        try:
            doc.setPlainText(datos.decode("utf-8-sig"))
        except UnicodeDecodeError:
            doc.setPlainText(datos.decode("cp1252", errors="replace"))
    doc.setModified(False)


def guardar(doc, ruta):
    ext = Path(ruta).suffix.lower()
    if ext == ".odt":
        odt.guardar(doc, ruta)
    elif ext == ".docx":
        guardar_atomico(ruta, lambda t: _guardar_docx(doc, t))
    elif ext in (".html", ".htm"):
        guardar_atomico(ruta, lambda t: Path(t).write_text(doc.toHtml(), encoding="utf-8"))
    elif ext == ".txt":
        guardar_atomico(ruta, lambda t: Path(t).write_text(doc.toPlainText(), encoding="utf-8"))
    else:
        raise ValueError(f"Extensión no soportada: {ext or '(ninguna)'}")
    doc.setModified(False)


def _guardar_docx(doc, ruta):
    import docx
    from docx.shared import Pt
    d = docx.Document()
    for p in list(d.paragraphs):
        p._element.getparent().remove(p._element)
    base = doc.defaultFont()  # sin esto Word y Writer aplican su propia fuente por defecto
    d.styles["Normal"].font.name, d.styles["Normal"].font.size = base.family(), Pt(base.pointSizeF())
    for n, t in odt.TAM_TITULO.items():
        d.styles[f"Heading {n}"].font.size = Pt(t)
    b = doc.begin()
    while b.isValid():
        n = b.blockFormat().headingLevel()
        estilo = f"Heading {n}" if n else None
        if b.textList():
            num = b.textList().format().style().name == "ListDecimal"
            estilo = "List Number" if num else "List Bullet"
        p = d.add_paragraph(style=estilo)
        al = b.blockFormat().alignment()
        p.alignment = (1 if al & Qt.AlignmentFlag.AlignHCenter else 2 if al & Qt.AlignmentFlag.AlignRight
                       else 3 if al & Qt.AlignmentFlag.AlignJustify else 0)
        it = b.begin()
        while not it.atEnd():
            fr, f = it.fragment(), it.fragment().charFormat()
            r = p.add_run(fr.text().replace(" ", "\n"))
            r.bold = f.fontWeight() >= QFont.Weight.Bold or None
            r.italic = f.fontItalic() or None
            r.underline = f.fontUnderline() or None
            r.font.strike = f.fontStrikeOut() or None
            if f.fontFamilies():
                r.font.name = f.fontFamilies()[0]
            if f.fontPointSize() > 0:
                r.font.size = Pt(f.fontPointSize())
            it += 1
        b = b.next()
    d.save(ruta)


def _abrir_docx(ruta, doc):
    import docx
    d = docx.Document(ruta)
    doc.clear()
    cur, primero = QTextCursor(doc), True
    for p in d.paragraphs:
        bf = QTextBlockFormat()
        bf.setAlignment({1: Qt.AlignmentFlag.AlignHCenter, 2: Qt.AlignmentFlag.AlignRight,
                         3: Qt.AlignmentFlag.AlignJustify}.get(p.alignment, Qt.AlignmentFlag.AlignLeft))
        nombre = p.style.name
        nivel = int(nombre[-1]) if nombre.startswith("Heading ") and nombre[-1].isdigit() else 0
        bf.setHeadingLevel(min(nivel, 6))
        if primero:
            cur.setBlockFormat(bf)
            primero = False
        else:
            cur.insertBlock(bf, QTextCharFormat())
        for r in p.runs:
            f = QTextCharFormat()
            if r.bold or nivel:
                f.setFontWeight(QFont.Weight.Bold)
            f.setFontItalic(bool(r.italic))
            f.setFontUnderline(bool(r.underline))
            f.setFontStrikeOut(bool(r.font.strike))
            if r.font.name:
                f.setFontFamilies([r.font.name])
            if r.font.size:
                f.setFontPointSize(r.font.size.pt)
            elif nivel:
                f.setFontPointSize(odt.TAM_TITULO.get(nivel, 13))
            cur.insertText(r.text, f)


class Candado:
    """Archivo .~lock.<nombre># para avisar que el documento está en uso."""

    def __init__(self, ruta):
        r = Path(ruta)
        self.ruta, self.propio = r.with_name(f".~lock.{r.name}#"), False

    def tomar(self):
        try:
            with open(self.ruta, "x", encoding="utf-8") as f:
                f.write(f",{getpass.getuser()},{socket.gethostname()},{datetime.now():%d.%m.%Y %H:%M};")
            self.propio = True
        except FileExistsError:
            pass
        except OSError:
            return True  # carpeta de solo lectura: se abre sin candado
        return self.propio

    def soltar(self):
        if self.propio and self.ruta.exists():
            os.unlink(self.ruta)
        self.propio = False
