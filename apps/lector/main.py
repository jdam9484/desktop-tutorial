"""Lector UNAMAD: réplica funcional de SumatraPDF con chat RAG sobre el documento."""
import html
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import pymupdf as fitz
from PyQt6.QtCore import QRectF, Qt, QTimer, QUrl, pyqtSignal
from PyQt6.QtGui import QAction, QColor, QImage, QKeySequence, QPainter, QPixmap
from PyQt6.QtPrintSupport import QPrintDialog, QPrinter
from PyQt6.QtWidgets import (QApplication, QCheckBox, QDockWidget, QFileDialog, QHBoxLayout, QLabel, QLineEdit,
                             QMainWindow, QMessageBox, QPushButton, QScrollArea, QSpinBox, QTabWidget, QTextBrowser,
                             QTreeWidget, QTreeWidgetItem, QVBoxLayout, QWidget)

from apps.comun import ia
from apps.comun.archivos import RAIZ, guardar_atomico
from apps.lector import rag

CONFIG = RAIZ / "lector_config.json"
SEP = 10


class Hoja(QWidget):
    """Dibuja todas las páginas en modo continuo, renderizando solo las visibles."""

    def __init__(self, vista):
        super().__init__()
        self.v = vista
        self.cache = {}

    def distribuir(self):
        self.cache.clear()
        self.rects, y, ancho = [], SEP, 0
        for p in self.v.doc:
            w, h = p.rect.width, p.rect.height
            if self.v.rot % 180:
                w, h = h, w
            w, h = w * self.v.zoom, h * self.v.zoom
            self.rects.append([0, y, w, h])
            y += h + SEP
            ancho = max(ancho, w)
        vp = self.v.viewport().width()
        for r in self.rects:
            r[0] = max(0, (max(vp, ancho) - r[2]) / 2)
        self.setMinimumSize(int(ancho), int(y))
        self.resize(max(vp, int(ancho)), int(y))
        self.update()

    def matriz(self):
        return fitz.Matrix(self.v.zoom, self.v.zoom).prerotate(self.v.rot)

    def pix(self, i):
        if i not in self.cache:
            dpr = self.devicePixelRatioF()
            m = fitz.Matrix(self.v.zoom * dpr, self.v.zoom * dpr).prerotate(self.v.rot)
            px = self.v.doc[i].get_pixmap(matrix=m, alpha=False)
            q = QImage(px.samples, px.width, px.height, px.stride, QImage.Format.Format_RGB888).copy()
            q.setDevicePixelRatio(dpr)
            self.cache[i] = QPixmap.fromImage(q)
            while len(self.cache) > 12:
                self.cache.pop(next(iter(self.cache)))
        return self.cache[i]

    def paintEvent(self, e):
        p = QPainter(self)
        p.fillRect(e.rect(), QColor("#f0f0f0"))
        for i, (x, y, w, h) in enumerate(self.rects):
            if y > e.rect().bottom() or y + h < e.rect().top():
                continue
            p.drawPixmap(int(x), int(y), self.pix(i))
            if i in self.v.hallazgos:
                pag = self.v.doc[i]
                m = self.matriz()
                base = pag.rect * m
                for k, r in enumerate(self.v.hallazgos[i]):
                    t = r * m
                    act = self.v.actual == (i, k)
                    p.fillRect(QRectF(x + t.x0 - base.x0, y + t.y0 - base.y0, t.width, t.height),
                               QColor(255, 140, 0, 130) if act else QColor(255, 255, 0, 110))


class Vista(QScrollArea):
    pagina = pyqtSignal(int)

    def __init__(self, ruta):
        super().__init__()
        self.ruta = str(ruta)
        self.doc = fitz.open(self.ruta)
        if self.doc.needs_pass:
            raise ValueError("El documento está protegido con contraseña.")
        self.zoom, self.rot, self.modo = 1.0, 0, "ancho"
        self.hallazgos, self.lista_h, self.actual = {}, [], None
        self.favoritos, self.indice, self.historial = [], None, []
        self.setWidgetResizable(False)
        self.hoja = Hoja(self)
        self.hoja.distribuir()
        self.setWidget(self.hoja)
        self.verticalScrollBar().valueChanged.connect(lambda *_: self.pagina.emit(self.pag()))

    def pag(self):
        c = self.verticalScrollBar().value() + self.viewport().height() / 3
        for i, (_, y, _, h) in enumerate(self.hoja.rects):
            if c < y + h + SEP:
                return i + 1
        return len(self.doc)

    def ir(self, n):
        n = max(1, min(n, len(self.doc)))
        self.verticalScrollBar().setValue(int(self.hoja.rects[n - 1][1] - SEP))
        self.pagina.emit(n)

    def poner(self, zoom=None, rot=None):
        n = self.pag()
        if zoom is not None:
            self.zoom = max(0.1, min(6.0, zoom))
        if rot is not None:
            self.rot = rot % 360
        self.hoja.distribuir()
        self.ir(n)

    def ajustar(self, modo):
        self.modo = modo
        r = self.doc[self.pag() - 1].rect
        w, h = (r.height, r.width) if self.rot % 180 else (r.width, r.height)
        z = (self.viewport().width() - 24) / w
        if modo == "pagina":
            z = min(z, (self.viewport().height() - 2 * SEP) / h)
        self.poner(zoom=z)

    def resizeEvent(self, e):
        super().resizeEvent(e)
        if self.modo and self.viewport().width() > 100:
            self.ajustar(self.modo)

    def buscar(self, t, mayus):
        self.hallazgos, self.lista_h, self.actual = {}, [], None
        if t:
            for i, p in enumerate(self.doc):
                rs = p.search_for(t)
                if mayus:  # search_for ignora mayúsculas: se filtra por el texto real del recuadro
                    rs = [r for r in rs if t in p.get_textbox(r + (-1, -1, 1, 1))]
                if rs:
                    self.hallazgos[i] = rs
                    self.lista_h += [(i, k) for k in range(len(rs))]
        self.hoja.update()
        return len(self.lista_h)

    def siguiente(self, paso):
        if not self.lista_h:
            return
        if self.actual is None:
            ini = [j for j, (i, _) in enumerate(self.lista_h) if i >= self.pag() - 1]
            j = (ini[0] if ini else 0) if paso > 0 else len(self.lista_h) - 1
        else:
            j = (self.lista_h.index(self.actual) + paso) % len(self.lista_h)
        self.actual = self.lista_h[j]
        i, k = self.actual
        t = self.hallazgos[i][k] * self.hoja.matriz()
        base = self.doc[i].rect * self.hoja.matriz()
        self.verticalScrollBar().setValue(int(self.hoja.rects[i][1] + t.y0 - base.y0 - self.viewport().height() / 3))
        self.hoja.update()


class Lector(QMainWindow):
    def __init__(self, ruta=None, config=CONFIG):
        super().__init__()
        self.resize(1280, 900)
        self.config, self.tarea = Path(config), None
        self.estado = self._leer_config()
        self.tabs = QTabWidget()
        self.tabs.setTabsClosable(True)
        self.tabs.tabCloseRequested.connect(self.cerrar_tab)
        self.tabs.currentChanged.connect(self._al_cambiar)
        self.setCentralWidget(self.tabs)
        self._barra()
        self._panel_indice()
        self._panel_chat()
        self.setWindowTitle("Lector UNAMAD")
        if ruta:
            self.abrir(ruta)

    @property
    def v(self):
        return self.tabs.currentWidget()

    # ------------------------------------------------------------ configuración
    def _leer_config(self):
        try:
            return json.loads(self.config.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return {}

    def _recordar(self, v):
        self.estado[v.ruta] = dict(PageNo=v.pag(), Zoom=v.zoom, Rotation=v.rot, DisplayMode=v.modo,
                                   Favorites=v.favoritos)

    # ------------------------------------------------------------ interfaz
    def _acc(self, t, fn, atajos=(), tip=None):
        a = QAction(t, self)
        a.setShortcuts([QKeySequence(x) for x in atajos])
        a.setToolTip((tip or t) + (f" ({atajos[0]})" if atajos else ""))
        a.triggered.connect(lambda *_: fn())
        return a

    def _con(self, fn):
        return lambda: fn(self.v) if self.v else None

    def _barra(self):
        tb = self.addToolBar("Principal")
        tb.setMovable(False)
        c = self._con
        tb.addAction(self._acc("Abrir", self.dlg_abrir, ["Ctrl+O"]))
        tb.addAction(self._acc("Imprimir", self.imprimir, ["Ctrl+P"]))
        tb.addSeparator()
        tb.addWidget(QLabel(" Página: "))
        self.sp = QSpinBox()
        self.sp.setMinimum(1)
        self.sp.editingFinished.connect(lambda: self.v and self.v.ir(self.sp.value()))
        tb.addWidget(self.sp)
        self.l_tot = QLabel(" / 0 ")
        tb.addWidget(self.l_tot)
        tb.addAction(self._acc("←", c(lambda v: v.ir(v.pag() - 1)), ["P"], "Página anterior"))
        tb.addAction(self._acc("→", c(lambda v: v.ir(v.pag() + 1)), ["N"], "Página siguiente"))
        tb.addSeparator()
        tb.addAction(self._acc("Ancho", c(lambda v: v.ajustar("ancho")), ["Ctrl+2"], "Ajustar al ancho"))
        tb.addAction(self._acc("1 pág.", c(lambda v: v.ajustar("pagina")), ["Ctrl+1"], "Ajustar a una página"))
        tb.addAction(self._acc("⟲", c(lambda v: v.poner(rot=v.rot - 90)), ["Ctrl+Shift+-"], "Girar a la izquierda"))
        tb.addAction(self._acc("⟳", c(lambda v: v.poner(rot=v.rot + 90)), ["Ctrl+Shift++"], "Girar a la derecha"))
        tb.addAction(self._acc("−", c(lambda v: self._zoom(v, 1 / 1.2)), ["Ctrl+-"], "Reducir"))
        tb.addAction(self._acc("+", c(lambda v: self._zoom(v, 1.2)), ["Ctrl++", "Ctrl+="], "Ampliar"))
        tb.addSeparator()
        tb.addWidget(QLabel(" Buscar: "))
        self.q = QLineEdit()
        self.q.setMaximumWidth(170)
        self.q.returnPressed.connect(self._buscar)
        tb.addWidget(self.q)
        tb.addAction(self._acc("‹", c(lambda v: self._sig(v, -1)), ["Shift+F3"], "Buscar anterior"))
        tb.addAction(self._acc("›", c(lambda v: self._sig(v, 1)), ["F3"], "Buscar siguiente"))
        self.may = QCheckBox("Aa")
        self.may.toggled.connect(lambda *_: self._buscar())
        tb.addWidget(self.may)
        self.l_h = QLabel()
        tb.addWidget(self.l_h)
        tb.addSeparator()
        tb.addAction(self._acc("★", c(self._favorito), ["Ctrl+B"], "Marcar página como favorita"))
        self.addAction(self._acc("Buscar", self.q.setFocus, ["Ctrl+F"]))

    def _panel_indice(self):
        self.arbol = QTreeWidget()
        self.arbol.setHeaderHidden(True)
        self.arbol.itemClicked.connect(lambda i, _: self.v and i.data(0, 32) and self.v.ir(i.data(0, 32)))
        d = QDockWidget("Marcadores")
        d.setWidget(self.arbol)
        self.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, d)
        self.resizeDocks([d], [190], Qt.Orientation.Horizontal)

    def _panel_chat(self):
        w = QWidget()
        l = QVBoxLayout(w)
        self.chat = QTextBrowser()
        self.chat.setOpenLinks(False)
        self.chat.anchorClicked.connect(self._cita)
        l.addWidget(self.chat)
        h = QHBoxLayout()
        self.preg = QLineEdit()
        self.preg.setPlaceholderText("Pregunte sobre el documento…")
        self.preg.returnPressed.connect(self.preguntar)
        self.b_env = QPushButton("Enviar")
        self.b_env.clicked.connect(self.preguntar)
        b = QPushButton("Detener")
        b.clicked.connect(lambda: self.tarea and self.tarea.cancelar.set())
        for x in (self.preg, self.b_env, b):
            h.addWidget(x)
        l.addLayout(h)
        d = QDockWidget("Chat con el PDF (IA local)")
        d.setWidget(w)
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, d)
        self.resizeDocks([d], [360], Qt.Orientation.Horizontal)

    # ------------------------------------------------------------ documento
    def dlg_abrir(self):
        fs, _ = QFileDialog.getOpenFileNames(self, "Abrir", "", "Documentos (*.pdf *.xps *.epub *.cbz)")
        for f in fs:
            self.abrir(f)

    def abrir(self, ruta):
        try:
            v = Vista(Path(ruta).resolve())
        except Exception as e:
            QMessageBox.warning(self, "Error", f"No se pudo abrir:\n{e}")
            return None
        e = self.estado.get(v.ruta, {})
        v.favoritos = list(e.get("Favorites", []))
        v.pagina.connect(self._pagina)
        self.tabs.setCurrentIndex(self.tabs.addTab(v, Path(ruta).name[:30]))
        v.rot, v.modo = e.get("Rotation", 0), e.get("DisplayMode", "ancho")

        def restaurar():
            if v.modo:
                v.ajustar(v.modo)
            else:
                v.poner(zoom=e.get("Zoom", 1.0))
            v.ir(e.get("PageNo", 1))
        QTimer.singleShot(0, restaurar)
        self._al_cambiar()
        return v

    def cerrar_tab(self, i):
        v = self.tabs.widget(i)
        if self.tarea and self.tarea.isRunning():
            self.tarea.cancelar.set()
            self.tarea.wait(3000)
        self._recordar(v)
        self.tabs.removeTab(i)
        v.doc.close()
        v.deleteLater()

    def _al_cambiar(self, *_):
        self.arbol.clear()
        self.chat.clear()
        v = self.v
        if not v:
            return
        self.sp.setMaximum(len(v.doc))
        self.l_tot.setText(f" / {len(v.doc)} ")
        self.setWindowTitle(f"{Path(v.ruta).name} - Lector UNAMAD")
        pila = [(0, self.arbol.invisibleRootItem())]
        for niv, tit, pg in v.doc.get_toc():
            while pila[-1][0] >= niv:
                pila.pop()
            it = QTreeWidgetItem(pila[-1][1], [tit])
            it.setData(0, 32, pg)
            pila.append((niv, it))
        for n in v.favoritos:
            it = QTreeWidgetItem(self.arbol, [f"★ Página {n}"])
            it.setData(0, 32, n)
        self.arbol.expandAll()
        self._pagina(v.pag())

    def _pagina(self, n):
        self.sp.blockSignals(True)
        self.sp.setValue(n)
        self.sp.blockSignals(False)

    def _zoom(self, v, k):
        v.modo = None
        v.poner(zoom=v.zoom * k)

    def _favorito(self, v):
        n = v.pag()
        v.favoritos = sorted(set(v.favoritos) ^ {n})
        self._al_cambiar()

    def _buscar(self):
        if self.v:
            n = self.v.buscar(self.q.text(), self.may.isChecked())
            self.l_h.setText(f" {n} resultados" if self.q.text() else "")
            self.v.siguiente(1)

    def _sig(self, v, paso):
        v.siguiente(paso) if v.lista_h else self._buscar()

    def imprimir(self):
        if not self.v:
            return
        pr = QPrinter(QPrinter.PrinterMode.HighResolution)
        if not QPrintDialog(pr, self).exec():
            return
        p = QPainter(pr)
        for i, pag in enumerate(self.v.doc):
            if i:
                pr.newPage()
            px = pag.get_pixmap(dpi=200, alpha=False)
            q = QImage(px.samples, px.width, px.height, px.stride, QImage.Format.Format_RGB888)
            r = p.viewport()
            t = q.size().scaled(r.size(), Qt.AspectRatioMode.KeepAspectRatio)
            p.drawImage(r.x(), r.y(), q.scaled(t))
        p.end()

    # ------------------------------------------------------------ chat RAG
    def preguntar(self):
        t, v = self.preg.text().strip(), self.v
        if not t or not v or (self.tarea and self.tarea.isRunning()):
            return
        self.preg.clear()
        self.b_env.setEnabled(False)
        self.previo = self.chat.toHtml()
        self.pregunta, self.resp = t, ""

        def fn(cancelar, emitir):
            if v.indice is None:
                emitir(("info", "Indexando documento…"))
                paginas, filas = rag.extraer(v.ruta)
                v.indice = rag.IndiceRAG(paginas, filas=filas).construir(cancelar, lambda p: emitir(("info", f"Indexando… {p} %")))
                if v.indice is None:
                    return ""
            total = ""
            for x in v.indice.responder(t, v.historial, cancelar):
                total += x
                emitir(("txt", x))
            return total

        def avance(m):
            if m[0] == "txt":
                self.resp += m[1]
            self._mostrar(m[1] if m[0] == "info" else self.resp)

        def fin(total):
            v.historial += [{"role": "user", "content": t}, {"role": "assistant", "content": total}]
            self._mostrar(total)
        self.tarea = ia.Tarea(fn)
        self.tarea.avance.connect(avance)
        self.tarea.lista.connect(fin)
        self.tarea.fallo.connect(lambda m: self._mostrar("Error: " + m))
        self.tarea.finished.connect(lambda: self.b_env.setEnabled(True))
        self.tarea.start()

    def _mostrar(self, r):
        h = html.escape(r).replace("\n", "<br>")
        h = re.sub(r"p[áa]g\.?\s*(\d+)", r'<a href="pag:\1">pág. \1</a>', h, flags=re.I)
        self.chat.setHtml(f"{self.previo}<p><b>Tú:</b> {html.escape(self.pregunta)}</p><p><b>IA:</b> {h}</p>")
        self.chat.verticalScrollBar().setValue(self.chat.verticalScrollBar().maximum())

    def _cita(self, url: QUrl):
        n = re.findall(r"\d+", url.toString())
        if n and self.v:
            self.v.ir(int(n[0]))

    def closeEvent(self, e):
        ia.detener_todas()
        for i in range(self.tabs.count()):
            self._recordar(self.tabs.widget(i))
        try:
            guardar_atomico(self.config, lambda t: Path(t).write_text(
                json.dumps(self.estado, ensure_ascii=False, indent=1), encoding="utf-8"))
        except OSError:
            pass
        e.accept()


def main():
    app = QApplication(sys.argv)
    w = Lector(sys.argv[1] if len(sys.argv) > 1 else None)
    w.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
