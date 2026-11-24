"""Escritor UNAMAD: réplica funcional de OpenOffice Writer con corrector, resumen y autocompletado por IA."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from PyQt6.QtCore import QEvent, Qt
from PyQt6.QtGui import (QAction, QColor, QFont, QKeySequence, QPdfWriter, QTextBlockFormat, QTextCharFormat,
                         QTextCursor, QTextDocument, QTextListFormat)
from PyQt6.QtPrintSupport import QPrintDialog, QPrinter
from PyQt6.QtWidgets import (QApplication, QColorDialog, QComboBox, QDockWidget, QFileDialog, QFontComboBox,
                             QHBoxLayout, QInputDialog, QLabel, QLineEdit, QMainWindow, QMessageBox, QPushButton,
                             QSlider, QTextEdit, QVBoxLayout, QWidget)

from apps.comun import ia
from apps.escritor import formatos

SISTEMA = "Eres un corrector profesional de español. Responde solo con el texto pedido, sin comentarios ni comillas."


class Escritor(QMainWindow):
    def __init__(self, ruta=None):
        super().__init__()
        self.ruta, self.candado, self.tarea = None, None, None
        self.ini_prop = None
        self.resize(1180, 800)
        self.ed = QTextEdit()
        self.ed.setFixedWidth(760)
        self.ed.setMinimumHeight(500)
        self.ed.setFont(QFont("Times New Roman", 12))  # el zoom parte de esta fuente
        self.ed.document().setDefaultFont(QFont("Times New Roman", 12))
        self.ed.document().setDocumentMargin(56)
        self.ed.setStyleSheet("QTextEdit{background:white;color:black;border:1px solid #555}")
        fondo = QWidget()
        fondo.setStyleSheet("background:#ababab")
        lay = QHBoxLayout(fondo)
        lay.addWidget(self.ed, alignment=Qt.AlignmentFlag.AlignHCenter)
        self.ed.setSizePolicy(self.ed.sizePolicy().horizontalPolicy(), self.ed.sizePolicy().Policy.Expanding)
        lay.setStretch(0, 1)
        self.setCentralWidget(fondo)
        self._menus()
        self._barra_formato()
        self._panel_ia()
        self._estado()
        self.ed.installEventFilter(self)
        self.ed.textChanged.connect(self._contar)
        self.ed.currentCharFormatChanged.connect(self._reflejar)
        self.ed.document().modificationChanged.connect(self._titulo)
        self._contar()
        self._titulo()
        if ruta:
            self.abrir(ruta)

    # ---------------------------------------------------------------- interfaz
    def _acc(self, texto, fn, atajo=None):
        a = QAction(texto, self)
        if atajo:
            a.setShortcut(QKeySequence(atajo))
        a.triggered.connect(lambda *_: fn())
        return a

    def _menus(self):
        mb, ed = self.menuBar(), self.ed
        A = self._acc
        self.acc = {}
        datos = {
            "&Archivo": [("Nuevo", self.nuevo, "Ctrl+N"), ("Abrir…", self.dlg_abrir, "Ctrl+O"),
                         ("Guardar", self.guardar, "Ctrl+S"), ("Guardar como…", self.guardar_como, "Ctrl+Shift+S"),
                         ("Exportar a PDF…", self.exportar_pdf, None), ("Imprimir…", self.imprimir, "Ctrl+P"),
                         ("Salir", self.close, "Ctrl+Q")],
            "&Editar": [("Deshacer", ed.undo, "Ctrl+Z"), ("Rehacer", ed.redo, "Ctrl+Y"), ("Cortar", ed.cut, "Ctrl+X"),
                        ("Copiar", ed.copy, "Ctrl+C"), ("Pegar", ed.paste, "Ctrl+V"),
                        ("Seleccionar todo", ed.selectAll, "Ctrl+A"), ("Buscar y reemplazar", self.buscar, "Ctrl+F")],
            "&Ver": [("Ampliar", lambda: self.zoom.setValue(self.zoom.value() + 10), "Ctrl++"),
                     ("Reducir", lambda: self.zoom.setValue(self.zoom.value() - 10), "Ctrl+-")],
            "&Insertar": [("Fecha", self.insertar_fecha, None), ("Línea horizontal", lambda: ed.insertHtml("<hr>"), None)],
            "F&ormato": [("Negrita", self.negrita, "Ctrl+B"), ("Cursiva", self.cursiva, "Ctrl+I"),
                         ("Subrayado", self.subrayado, "Ctrl+U"), ("Tachado", self.tachado, None),
                         ("Viñetas", lambda: self.lista(False), None), ("Numeración", lambda: self.lista(True), None)],
            "&Herramientas": [("Corregir estilo (IA)", self.ia_corregir, "F7"), ("Resumir (IA)", self.ia_resumir, "F8"),
                              ("Autocompletar (IA)", self.ia_completar, "Ctrl+Space"),
                              ("Contar palabras", self.contar_dialogo, None)],
            "A&yuda": [("Acerca de", lambda: QMessageBox.information(
                self, "Acerca de", "Escritor UNAMAD\nRéplica funcional académica de Writer con IA local."), None)],
        }
        for m, its in datos.items():
            menu = mb.addMenu(m)
            for t, f, k in its:
                self.acc[t] = A(t, f, k)
                menu.addAction(self.acc[t])
        tb = self.addToolBar("Estándar")
        for t in ("Nuevo", "Abrir…", "Guardar", "Exportar a PDF…", "Imprimir…", "Deshacer", "Rehacer",
                  "Buscar y reemplazar"):
            tb.addAction(self.acc[t])

    def _barra_formato(self):
        self.addToolBarBreak()
        tb = self.addToolBar("Formato")
        self.estilo = QComboBox()
        self.estilo.addItems(["Predeterminado", "Encabezado 1", "Encabezado 2", "Encabezado 3"])
        self.estilo.activated.connect(self.aplicar_estilo)
        self.fuente = QFontComboBox()
        self.fuente.setMaximumWidth(190)
        self.fuente.setCurrentFont(QFont("Times New Roman"))
        self.fuente.textActivated.connect(lambda t: self._fmt(lambda f: f.setFontFamilies([t])))
        self.tam = QComboBox()
        self.tam.setEditable(True)
        self.tam.addItems([str(x) for x in (8, 9, 10, 11, 12, 14, 16, 18, 20, 24, 28, 36, 48)])
        self.tam.setCurrentText("12")
        self.tam.textActivated.connect(self._tamano)
        for w in (self.estilo, self.fuente, self.tam):
            tb.addWidget(w)
        for t, f, tip in (("N", self.negrita, "Negrita"), ("C", self.cursiva, "Cursiva"),
                          ("S", self.subrayado, "Subrayado")):
            a = self._acc(t, f)
            a.setToolTip(tip)
            tb.addAction(a)
        tb.addSeparator()
        for t, al in (("Izq", Qt.AlignmentFlag.AlignLeft), ("Cen", Qt.AlignmentFlag.AlignHCenter),
                      ("Der", Qt.AlignmentFlag.AlignRight), ("Jus", Qt.AlignmentFlag.AlignJustify)):
            tb.addAction(self._acc(t, lambda al=al: self.ed.setAlignment(al)))
        tb.addSeparator()
        tb.addAction(self._acc("1. Lista", lambda: self.lista(True)))
        tb.addAction(self._acc("• Lista", lambda: self.lista(False)))
        tb.addAction(self._acc("Color", lambda: self._color(False)))
        tb.addAction(self._acc("Resaltar", lambda: self._color(True)))

    def _panel_ia(self):
        w = QWidget()
        v = QVBoxLayout(w)
        v.addWidget(QLabel("<b>Asistente de IA (local)</b><br>Use la selección o todo el texto."))
        for t, f in (("Corregir estilo (F7)", self.ia_corregir), ("Resumir (F8)", self.ia_resumir),
                     ("Autocompletar (Ctrl+Espacio)", self.ia_completar)):
            b = QPushButton(t)
            b.clicked.connect(lambda _, f=f: f())
            v.addWidget(b)
        self.salida = QTextEdit()
        self.salida.setPlaceholderText("Aquí aparecerá la propuesta.")
        v.addWidget(self.salida)
        h = QHBoxLayout()
        self.b_ap = QPushButton("Reemplazar selección")
        self.b_ap.clicked.connect(self.aplicar)
        self.b_ap.setEnabled(False)
        self.b_no = QPushButton("Detener")
        self.b_no.clicked.connect(self.detener)
        self.b_no.setEnabled(False)
        h.addWidget(self.b_ap)
        h.addWidget(self.b_no)
        v.addLayout(h)
        d = QDockWidget("Propiedades e IA")
        d.setWidget(w)
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, d)

    def _estado(self):
        s = self.statusBar()
        self.l_pal = QLabel()
        self.zoom = QSlider(Qt.Orientation.Horizontal)
        self.zoom.setRange(50, 200)
        self.zoom.setValue(100)
        self.zoom.setFixedWidth(130)
        self.l_zoom = QLabel("100 %")
        self._z = 100
        self.zoom.valueChanged.connect(self._zoom)
        s.addWidget(self.l_pal)
        for w in (QLabel("Español (Perú)"), QLabel("INSERT"), self.zoom, self.l_zoom):
            s.addPermanentWidget(w)

    def _zoom(self, v):
        """Amplía la vista sin tocar los tamaños guardados en el documento."""
        pasos = (v - self._z) // 10
        self.ed.zoomIn(pasos) if pasos > 0 else self.ed.zoomOut(-pasos)
        self._z += pasos * 10
        self.l_zoom.setText(f"{self._z} %")

    def _contar(self):
        t = self.ed.toPlainText()
        self.l_pal.setText(f"Página 1/{max(1, -(-int(self.ed.document().size().height()) // 1075))}   "
                           f"{len(t.split())} palabras, {len(t)} caracteres")

    def _titulo(self, *_):
        self.setWindowTitle(f"{'*' if self.ed.document().isModified() else ''}"
                            f"{Path(self.ruta).name if self.ruta else 'Sin título 1'} - Escritor UNAMAD")

    def _reflejar(self, f):
        if f.fontFamilies():
            self.fuente.setCurrentFont(QFont(f.fontFamilies()[0]))
        self.tam.setCurrentText(f"{f.fontPointSize() or 12:g}")

    # ---------------------------------------------------------------- formato
    def _fmt(self, cambio):
        f = QTextCharFormat()
        cambio(f)
        self.ed.mergeCurrentCharFormat(f)
        self.ed.setFocus()

    def negrita(self):
        on = self.ed.fontWeight() >= QFont.Weight.Bold
        self._fmt(lambda f: f.setFontWeight(QFont.Weight.Normal if on else QFont.Weight.Bold))

    def cursiva(self):
        on = self.ed.fontItalic()
        self._fmt(lambda f: f.setFontItalic(not on))

    def subrayado(self):
        on = self.ed.fontUnderline()
        self._fmt(lambda f: f.setFontUnderline(not on))

    def tachado(self):
        on = self.ed.currentCharFormat().fontStrikeOut()
        self._fmt(lambda f: f.setFontStrikeOut(not on))

    def _tamano(self, t):
        try:
            n = float(t)
        except ValueError:
            return
        if n > 0:
            self._fmt(lambda f: f.setFontPointSize(n))

    def _color(self, fondo):
        c = QColorDialog.getColor(QColor("yellow" if fondo else "black"), self)
        if c.isValid():
            self._fmt(lambda f: f.setBackground(c) if fondo else f.setForeground(c))

    def lista(self, num):
        lf = QTextListFormat()
        lf.setStyle(QTextListFormat.Style.ListDecimal if num else QTextListFormat.Style.ListDisc)
        self.ed.textCursor().createList(lf)

    def aplicar_estilo(self, n):
        c = self.ed.textCursor()
        c.beginEditBlock()
        bf = QTextBlockFormat()
        bf.setHeadingLevel(n)
        c.mergeBlockFormat(bf)
        c.select(QTextCursor.SelectionType.BlockUnderCursor)
        f = QTextCharFormat()
        f.setFontPointSize({0: 12, 1: 20, 2: 16, 3: 14}[n])
        f.setFontWeight(QFont.Weight.Bold if n else QFont.Weight.Normal)
        c.mergeCharFormat(f)
        c.endEditBlock()

    def insertar_fecha(self):
        from datetime import date
        self.ed.insertPlainText(date.today().strftime("%d/%m/%Y"))

    def contar_dialogo(self):
        QMessageBox.information(self, "Contar palabras", self.l_pal.text())

    def buscar(self):
        t, ok = QInputDialog.getText(self, "Buscar", "Texto:", QLineEdit.EchoMode.Normal,
                                     self.ed.textCursor().selectedText())
        if not ok or not t:
            return
        r, ok = QInputDialog.getText(self, "Reemplazar todo", f"Reemplazar «{t}» por (Cancelar = solo buscar):")
        if not ok:
            if not self.ed.find(t):
                self.ed.moveCursor(QTextCursor.MoveOperation.Start)
                if not self.ed.find(t):
                    self.statusBar().showMessage("No se encontró", 4000)
            return
        self.statusBar().showMessage(f"{self.reemplazar_todo(t, r)} reemplazos", 4000)

    def reemplazar_todo(self, t, r):
        doc, n, pos = self.ed.document(), 0, 0
        c0 = QTextCursor(doc)
        c0.beginEditBlock()
        while True:
            c = doc.find(t, pos)
            if c.isNull():
                break
            c.insertText(r)
            pos = c.position()
            n += 1
        c0.endEditBlock()
        return n

    # ---------------------------------------------------------------- archivos
    def _descartar(self):
        if not self.ed.document().isModified():
            return True
        r = QMessageBox.question(self, "Cambios sin guardar", "¿Guardar los cambios?",
                                 QMessageBox.StandardButton.Save | QMessageBox.StandardButton.Discard |
                                 QMessageBox.StandardButton.Cancel)
        if r == QMessageBox.StandardButton.Save:
            return self.guardar()
        return r == QMessageBox.StandardButton.Discard

    def nuevo(self):
        if self._descartar():
            if self.candado:
                self.candado.soltar()
            self.ed.clear()
            self.ruta = None
            self.ed.document().setModified(False)
            self._titulo()

    def dlg_abrir(self):
        if self._descartar():
            f, _ = QFileDialog.getOpenFileName(self, "Abrir", "", formatos.FILTRO)
            if f:
                self.abrir(f)

    def abrir(self, f):
        nuevo = formatos.Candado(f)
        libre = nuevo.tomar()
        try:
            formatos.abrir(f, self.ed.document())
        except Exception as e:
            nuevo.soltar()
            QMessageBox.warning(self, "Error", f"No se pudo abrir:\n{e}")
            return False
        if self.candado:
            self.candado.soltar()
        self.candado, self.ruta = nuevo, f
        if not libre:
            self.statusBar().showMessage("Aviso: otro programa tiene abierto este documento.", 8000)
        self._titulo()
        self._contar()
        return True

    def guardar(self):
        if not self.ruta:
            return self.guardar_como()
        try:
            self.zoom.setValue(100)  # la vista ampliada no debe alterar la fuente base
            formatos.guardar(self.ed.document(), self.ruta)
        except Exception as e:
            QMessageBox.warning(self, "Error", f"No se pudo guardar:\n{e}")
            return False
        self._titulo()
        self.statusBar().showMessage("Guardado", 3000)
        return True

    def guardar_como(self):
        f, _ = QFileDialog.getSaveFileName(self, "Guardar como", "documento.odt", formatos.FILTRO)
        if not f:
            return False
        if not Path(f).suffix:
            f += ".odt"
        self.ruta = f
        return self.guardar()

    def exportar_pdf(self):
        f, _ = QFileDialog.getSaveFileName(self, "Exportar", "documento.pdf", "PDF (*.pdf)")
        if f:
            self.ed.document().clone().print(QPdfWriter(f))

    def imprimir(self):
        p = QPrinter()
        if QPrintDialog(p, self).exec():
            self.ed.document().print(p)

    def closeEvent(self, e):
        if not self._descartar():
            e.ignore()
            return
        ia.detener_todas()
        if self.candado:
            self.candado.soltar()
        e.accept()

    # ---------------------------------------------------------------- IA
    def _texto_objetivo(self):
        c = self.ed.textCursor()
        if not c.hasSelection():
            c.select(QTextCursor.SelectionType.Document)
        self.rango = (c.selectionStart(), c.selectionEnd())
        return c.selectedText().replace(" ", "\n").replace(" ", "\n").strip()

    def _lanzar(self, mensajes, al_trozo, al_final=None, **kw):
        if self.tarea and self.tarea.isRunning():
            self.statusBar().showMessage("La IA todavía está trabajando. Pulse Detener.", 4000)
            return

        def fn(cancelar, emitir):
            total = ""
            for t in ia.chat(mensajes, cancelar=cancelar, **kw):
                total += t
                emitir(t)
            return total
        self.tarea = ia.Tarea(fn)
        self.tarea.avance.connect(al_trozo)
        self.tarea.fallo.connect(lambda m: (self.salida.setPlainText("Error: " + m)))
        if al_final:
            self.tarea.lista.connect(al_final)
        self.tarea.finished.connect(lambda: self.b_no.setEnabled(False))
        self.b_no.setEnabled(True)
        self.tarea.start()

    def _a_panel(self, t):
        c = self.salida.textCursor()
        c.movePosition(QTextCursor.MoveOperation.End)
        c.insertText(t)

    def ia_corregir(self):
        t = self._texto_objetivo()
        if not t:
            self.salida.setPlainText("Escriba o seleccione texto primero.")
            return
        if len(t.split()) > 600:  # más largo se truncaría y al reemplazar se perdería texto
            self.salida.setPlainText("Seleccione como máximo 600 palabras por corrección.")
            return
        self.salida.clear()
        self.b_ap.setEnabled(False)
        self._lanzar([{"role": "system", "content": SISTEMA},
                      {"role": "user", "content": "Corrige ortografía, gramática y estilo sin cambiar el significado ni "
                       "agregar información. Devuelve solo el texto corregido:\n\n" + t}],
                     self._a_panel, lambda _: self.b_ap.setEnabled(True), max_tokens=1500, temperatura=0.1)

    def ia_resumir(self):
        t = self._texto_objetivo()
        if len(t.split()) < 20:
            self.salida.setPlainText("Se necesitan al menos 20 palabras para resumir.")
            return
        if len(t.split()) > 1800:
            self.salida.setPlainText("Seleccione como máximo 1800 palabras por resumen.")
            return
        self.salida.clear()
        self.b_ap.setEnabled(False)
        self._lanzar([{"role": "system", "content": SISTEMA},
                      {"role": "user", "content": "Resume en español en un máximo de 3 oraciones:\n\n" + t}],
                     self._a_panel, max_tokens=300)

    def aplicar(self):
        t = self.salida.toPlainText().strip()
        if t:
            c = self.ed.textCursor()
            c.setPosition(self.rango[0])
            c.setPosition(self.rango[1], QTextCursor.MoveMode.KeepAnchor)
            c.insertText(t)
        self.b_ap.setEnabled(False)

    def detener(self):
        if self.tarea:
            self.tarea.cancelar.set()

    def ia_completar(self):
        c = self.ed.textCursor()
        previo = self.ed.toPlainText()[:c.position()][-1500:]
        if len(previo.strip()) < 10:
            self.statusBar().showMessage("Escriba un poco más para autocompletar.", 4000)
            return
        self.ini_prop = None
        self._lanzar([{"role": "system", "content": "Continúas textos en español. Responde SOLO con la continuación "
                       "inmediata (máximo 15 palabras), sin repetir lo escrito."},
                      {"role": "user", "content": previo}],
                     lambda t: None, self._proponer, modelo=ia.MODELO_RAPIDO, max_tokens=40, temperatura=0.3)

    def _proponer(self, t):
        t = " ".join(t.split())
        if not t:
            return
        c = self.ed.textCursor()
        antes = self.ed.toPlainText()[:c.position()]
        if antes and not antes[-1].isspace() and t[0] not in ".,;:)":
            t = " " + t
        f = QTextCharFormat(c.charFormat())
        f.setForeground(QColor("#999999"))
        self.ini_prop = c.position()
        c.insertText(t, f)
        self.fin_prop = c.position()
        self.statusBar().showMessage("Tab: aceptar   Esc: descartar")

    def eventFilter(self, o, e):
        if o is self.ed and e.type() == QEvent.Type.KeyPress and self.ini_prop is not None:
            aceptar = e.key() == Qt.Key.Key_Tab
            c = self.ed.textCursor()
            c.setPosition(self.ini_prop)
            c.setPosition(self.fin_prop, QTextCursor.MoveMode.KeepAnchor)
            if aceptar:
                t = c.selectedText()
                f = QTextCharFormat(c.charFormat())
                f.clearForeground()
                c.insertText(t, f)
            else:
                c.removeSelectedText()
            self.ini_prop = None
            self.statusBar().clearMessage()
            if aceptar or e.key() == Qt.Key.Key_Escape:
                return True
        return super().eventFilter(o, e)


def main():
    app = QApplication(sys.argv)
    v = Escritor(sys.argv[1] if len(sys.argv) > 1 else None)
    v.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
