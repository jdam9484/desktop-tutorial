"""Lienzo UNAMAD: réplica funcional de Paint con eliminación de fondo y reconocimiento de bocetos por IA."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from PyQt6.QtCore import QPoint, QPointF, QRect, QRectF, Qt, pyqtSignal
from PyQt6.QtGui import (QAction, QBrush, QColor, QImage, QKeySequence, QPainter, QPen, QPixmap, QTransform)
from PyQt6.QtWidgets import (QApplication, QButtonGroup, QColorDialog, QFileDialog, QGridLayout, QGroupBox,
                             QHBoxLayout, QInputDialog, QLabel, QMainWindow, QMessageBox, QPushButton, QScrollArea,
                             QSlider, QVBoxLayout, QWidget)

from apps.comun import ia, vision
from apps.lienzo import motor

COLORES = ["#000000", "#7f7f7f", "#880015", "#ed1c24", "#ff7f27", "#fff200", "#22b14c", "#00a2e8", "#3f48cc", "#a349a4",
           "#ffffff", "#c3c3c3", "#b97a57", "#ffaec9", "#ffc90e", "#efe4b0", "#b5e61d", "#99d9ea", "#7092be", "#c8bfe7"]
HERR = ["Seleccionar", "Lápiz", "Pincel", "Borrador", "Relleno", "Texto", "Cuentagotas"]
FILTRO = "Imágenes (*.png *.jpg *.jpeg *.bmp *.gif)"


class Lienzo(QWidget):
    movido = pyqtSignal(int, int)
    cambiado = pyqtSignal()
    color_tomado = pyqtSignal(QColor)

    def __init__(self):
        super().__init__()
        self.setMouseTracking(True)
        self.setFocusPolicy(Qt.FocusPolicy.ClickFocus)
        self.zoom, self.herr = 1.0, "Pincel"
        self.c1, self.c2 = QColor("black"), QColor("white")
        self.grosor, self.opacidad = 4, 255
        self.sel, self.ini, self.fin, self.base = None, None, None, None
        self.atras, self.adelante = [], []
        self.modificado = False
        self.img = QImage(1152, 720, QImage.Format.Format_ARGB32)
        self.img.fill(Qt.GlobalColor.white)
        self._ajustar()

    def _ajustar(self):
        self.setFixedSize(int(self.img.width() * self.zoom), int(self.img.height() * self.zoom))
        self.update()
        self.cambiado.emit()

    def poner_zoom(self, z):
        self.zoom = z
        self._ajustar()

    def recordar(self):
        self.atras = (self.atras + [self.img.copy()])[-30:]
        self.adelante.clear()
        self.modificado = True

    def reemplazar(self, img, recordar=True):
        if recordar:
            self.recordar()
        self.img, self.sel = img.convertToFormat(QImage.Format.Format_ARGB32), None
        self._ajustar()

    def deshacer(self):
        if self.atras:
            self.adelante.append(self.img.copy())
            self.img = self.atras.pop()
            self.sel = None
            self._ajustar()

    def rehacer(self):
        if self.adelante:
            self.atras.append(self.img.copy())
            self.img = self.adelante.pop()
            self.sel = None
            self._ajustar()

    def paintEvent(self, _):
        p = QPainter(self)
        p.fillRect(self.rect(), QBrush(QColor("#dddddd"), Qt.BrushStyle.Dense4Pattern))
        p.scale(self.zoom, self.zoom)
        p.drawImage(0, 0, self.img)
        if self.ini is not None and self.herr in motor.FORMAS:
            self._pintar_forma(p)
        r = self.sel if self.herr != "Seleccionar" or self.ini is None else QRect(self.ini, self.fin).normalized()
        if r:
            p.setPen(QPen(QColor("#0078d4"), 1 / self.zoom, Qt.PenStyle.DashLine))
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawRect(r)

    def _lapiz(self, color=None):
        c = QColor(color or self.c1)
        c.setAlpha(self.opacidad)
        g = 1 if self.herr == "Lápiz" else self.grosor
        return QPen(c, g, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin)

    def _pintar_forma(self, p):
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setPen(self._lapiz())
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawPath(motor.trazo_forma(self.herr, QPointF(self.ini), QPointF(self.fin)))

    def _trazar(self):
        """Redibuja el trazo completo sobre la base para que la opacidad no se acumule."""
        self.img = self.base.copy()
        p = QPainter(self.img)
        p.setRenderHint(QPainter.RenderHint.Antialiasing, self.herr != "Lápiz")
        if self.herr == "Borrador":
            p.setPen(QPen(self.c2, self.grosor * 3, Qt.PenStyle.SolidLine, Qt.PenCapStyle.SquareCap))
        else:
            p.setPen(self._lapiz())
        if len(self.pts) == 1:
            p.drawPoint(self.pts[0])
        else:
            p.drawPolyline(self.pts)
        p.end()
        self.update()

    def _pos(self, e):
        q = e.position() / self.zoom
        return QPoint(int(q.x()), int(q.y()))

    def mousePressEvent(self, e):
        if e.button() != Qt.MouseButton.LeftButton:
            return
        q, h = self._pos(e), self.herr
        if h == "Relleno":
            if self.img.rect().contains(q):
                c = QColor(self.c1)
                c.setAlpha(self.opacidad)
                self.reemplazar(motor.rellenar(self.img, q.x(), q.y(), c))
        elif h == "Cuentagotas":
            if self.img.rect().contains(q):
                self.color_tomado.emit(self.img.pixelColor(q))
        elif h == "Texto":
            t, ok = QInputDialog.getText(self, "Texto", "Texto:")
            if ok and t:
                self.recordar()
                p = QPainter(self.img)
                f = p.font()
                f.setPointSize(8 + self.grosor * 2)
                p.setFont(f)
                p.setPen(self.c1)
                p.drawText(q, t)
                p.end()
                self.update()
        else:
            self.ini = self.fin = q
            if h in ("Lápiz", "Pincel", "Borrador"):
                self.recordar()
                self.base, self.pts = self.img.copy(), [q]
                self._trazar()

    def mouseMoveEvent(self, e):
        q = self._pos(e)
        self.movido.emit(q.x(), q.y())
        if self.ini is None:
            return
        self.fin = q
        if self.herr in ("Lápiz", "Pincel", "Borrador"):
            self.pts.append(q)
            self._trazar()
        self.update()

    def mouseReleaseEvent(self, e):
        if self.ini is None:
            return
        if self.herr == "Seleccionar":
            r = QRect(self.ini, self.fin).normalized().intersected(self.img.rect())
            self.sel = r if r.width() > 2 and r.height() > 2 else None
        elif self.herr in motor.FORMAS:
            self.recordar()
            p = QPainter(self.img)
            self._pintar_forma(p)
            p.end()
        self.ini = self.fin = self.base = None
        self.update()
        self.cambiado.emit()


class Ventana(QMainWindow):
    def __init__(self, ruta=None):
        super().__init__()
        self.resize(1380, 860)
        self.ruta, self.tarea = None, None
        self.lz = Lienzo()
        sc = QScrollArea()
        sc.setWidget(self.lz)
        sc.setAlignment(Qt.AlignmentFlag.AlignCenter)
        centro = QWidget()
        v = QVBoxLayout(centro)
        v.addLayout(self._cinta())
        h = QHBoxLayout()
        h.addLayout(self._deslizadores())
        h.addWidget(sc, 1)
        v.addLayout(h, 1)
        self.setCentralWidget(centro)
        self._menus()
        self.l_xy, self.l_sel, self.l_tam, self.l_ia = QLabel(), QLabel(), QLabel(), QLabel()
        for w in (self.l_xy, self.l_sel, self.l_tam, self.l_ia):
            self.statusBar().addWidget(w)
        self.zoom = QSlider(Qt.Orientation.Horizontal)
        self.zoom.setRange(10, 400)
        self.zoom.setValue(100)
        self.zoom.setFixedWidth(140)
        self.l_z = QLabel("100 %")
        self.zoom.valueChanged.connect(lambda z: (self.lz.poner_zoom(z / 100), self.l_z.setText(f"{z} %")))
        self.statusBar().addPermanentWidget(self.zoom)
        self.statusBar().addPermanentWidget(self.l_z)
        self.lz.movido.connect(lambda x, y: self.l_xy.setText(f"{x}, {y} px"))
        self.lz.cambiado.connect(self._estado)
        self.lz.color_tomado.connect(lambda c: self._color(c))
        self._estado()
        if ruta:
            self.abrir(ruta)

    def _boton(self, t, fn, marca=False):
        b = QPushButton(t)
        b.setCheckable(marca)
        b.clicked.connect(lambda *_: fn())
        return b

    def _grupo(self, titulo, botones, col):
        g = QGroupBox(titulo)
        l = QGridLayout(g)
        l.setContentsMargins(4, 4, 4, 4)
        l.setSpacing(2)
        for i, b in enumerate(botones):
            l.addWidget(b, i // col, i % col)
        return g

    def _cinta(self):
        h = QHBoxLayout()
        self.gr = QButtonGroup(self)
        self.b_h = {}

        def herr(n):
            b = self._boton(n, lambda n=n: self._herr(n), True)
            self.gr.addButton(b)
            self.b_h[n] = b
            return b
        h.addWidget(self._grupo("Imagen", [
            self._boton("Recortar", self.recortar), self._boton("Girar", lambda: self.girar(90)),
            self._boton("Voltear H", lambda: self.voltear(True)), self._boton("Voltear V", lambda: self.voltear(False)),
            self._boton("Tamaño", self.redimensionar)], 3))
        h.addWidget(self._grupo("Herramientas", [herr(n) for n in HERR], 4))
        h.addWidget(self._grupo("Formas", [herr(n) for n in motor.FORMAS], 5))
        cg = QGroupBox("Colores")
        gl = QGridLayout(cg)
        gl.setSpacing(2)
        self.m1, self.m2 = QPushButton("1"), QPushButton("2")
        for m, k in ((self.m1, 1), (self.m2, 2)):
            m.setFixedSize(34, 26)
            m.clicked.connect(lambda _, k=k: self._elegir(k))
            gl.addWidget(m, k - 1, 0)
        for i, c in enumerate(COLORES):
            b = QPushButton()
            b.setFixedSize(22, 22)
            b.setStyleSheet(f"background:{c};border:1px solid #777;border-radius:11px")
            b.clicked.connect(lambda _, c=c: self._color(QColor(c)))
            gl.addWidget(b, i // 10, 1 + i % 10)
        h.addWidget(cg)
        self.b_fondo = self._boton("Quitar fondo", self.ia_fondo)
        self.b_boc = self._boton("Reconocer boceto", self.ia_boceto)
        h.addWidget(self._grupo("IA local", [self.b_fondo, self.b_boc], 1))
        h.addStretch()
        self.b_h["Pincel"].setChecked(True)
        self._color(QColor("black"))
        return h

    def _deslizadores(self):
        h = QVBoxLayout()
        for t, mx, val, fn in (("Grosor", 60, 4, lambda n: setattr(self.lz, "grosor", n)),
                               ("Opac.", 255, 255, lambda n: setattr(self.lz, "opacidad", n))):
            s = QSlider(Qt.Orientation.Vertical)
            s.setRange(1, mx)
            s.setValue(val)
            s.valueChanged.connect(fn)
            h.addWidget(QLabel(t))
            h.addWidget(s)
        return h

    def _menus(self):
        for m, its in {
            "&Archivo": [("Nuevo", self.nuevo, "Ctrl+N"), ("Abrir…", self.dlg_abrir, "Ctrl+O"),
                         ("Guardar", self.guardar, "Ctrl+S"), ("Guardar como…", self.guardar_como, "F12"),
                         ("Salir", self.close, "Alt+F4")],
            "&Editar": [("Deshacer", self.lz.deshacer, "Ctrl+Z"), ("Rehacer", self.lz.rehacer, "Ctrl+Y"),
                        ("Copiar", self.copiar, "Ctrl+C"), ("Pegar", self.pegar, "Ctrl+V"),
                        ("Seleccionar todo", self.sel_todo, "Ctrl+A"), ("Invertir colores", self.invertir, "Ctrl+Shift+I"),
                        ("Redimensionar…", self.redimensionar, "Ctrl+W")],
            "&Ver": [("Acercar", lambda: self.zoom.setValue(self.zoom.value() + 25), "Ctrl++"),
                     ("Alejar", lambda: self.zoom.setValue(self.zoom.value() - 25), "Ctrl+-"),
                     ("100 %", lambda: self.zoom.setValue(100), "Ctrl+0")],
        }.items():
            menu = self.menuBar().addMenu(m)
            for t, f, k in its:
                a = QAction(t, self)
                a.setShortcut(QKeySequence(k))
                a.triggered.connect(lambda _, f=f: f())
                menu.addAction(a)

    def _herr(self, n):
        self.lz.herr = n
        self.lz.ini = None

    def _color(self, c, k=1):
        setattr(self.lz, f"c{k}", c)
        for m, col in ((self.m1, self.lz.c1), (self.m2, self.lz.c2)):
            m.setStyleSheet(f"background:{col.name()};color:{'white' if col.lightness() < 128 else 'black'}")

    def _elegir(self, k):
        c = QColorDialog.getColor(getattr(self.lz, f"c{k}"), self)
        if c.isValid():
            self._color(c, k)

    def _estado(self):
        i, s = self.lz.img, self.lz.sel
        self.l_tam.setText(f"{i.width()} × {i.height()} píxeles")
        self.l_sel.setText(f"Sel. {s.width()} × {s.height()}" if s else "")
        n = Path(self.ruta).name if self.ruta else "Sin título"
        self.setWindowTitle(f"{'*' if self.lz.modificado else ''}{n} - Lienzo UNAMAD")

    # ------------------------------------------------------------ imagen
    def recortar(self):
        if self.lz.sel:
            self.lz.reemplazar(self.lz.img.copy(self.lz.sel))

    def girar(self, g):
        self.lz.reemplazar(self.lz.img.transformed(QTransform().rotate(g)))

    def voltear(self, hor):
        self.lz.reemplazar(self.lz.img.transformed(QTransform().scale(-1, 1) if hor else QTransform().scale(1, -1)))

    def invertir(self):
        i = self.lz.img.copy()
        i.invertPixels()
        self.lz.reemplazar(i)

    def redimensionar(self):
        n, ok = QInputDialog.getInt(self, "Cambiar de tamaño", "Porcentaje:", 100, 1, 500)
        if ok and n != 100:
            i = self.lz.img
            self.lz.reemplazar(i.scaled(max(1, i.width() * n // 100), max(1, i.height() * n // 100),
                                        Qt.AspectRatioMode.IgnoreAspectRatio,
                                        Qt.TransformationMode.SmoothTransformation))

    def sel_todo(self):
        self.lz.sel = self.lz.img.rect()
        self.lz.update()
        self._estado()

    def copiar(self):
        QApplication.clipboard().setImage(self.lz.img.copy(self.lz.sel) if self.lz.sel else self.lz.img)

    def pegar(self):
        i = QApplication.clipboard().image()
        if not i.isNull():
            self.lz.recordar()
            p = QPainter(self.lz.img)
            p.drawImage(0, 0, i)
            p.end()
            self.lz.update()

    # ------------------------------------------------------------ archivos
    def _descartar(self):
        if not self.lz.modificado:
            return True
        r = QMessageBox.question(self, "Lienzo", "¿Guardar los cambios?", QMessageBox.StandardButton.Save |
                                 QMessageBox.StandardButton.Discard | QMessageBox.StandardButton.Cancel)
        if r == QMessageBox.StandardButton.Save:
            return self.guardar()
        return r == QMessageBox.StandardButton.Discard

    def nuevo(self):
        if self._descartar():
            i = QImage(1152, 720, QImage.Format.Format_ARGB32)
            i.fill(Qt.GlobalColor.white)
            self.lz.reemplazar(i)
            self.ruta, self.lz.modificado = None, False
            self._estado()

    def dlg_abrir(self):
        if self._descartar():
            f, _ = QFileDialog.getOpenFileName(self, "Abrir", "", FILTRO)
            if f:
                self.abrir(f)

    def abrir(self, f):
        try:
            i = motor.abrir(f)
        except Exception as e:
            QMessageBox.warning(self, "Error", f"No se pudo abrir:\n{e}")
            return
        self.lz.reemplazar(i, False)
        self.lz.atras.clear()
        self.lz.adelante.clear()
        self.ruta, self.lz.modificado = f, False
        self._estado()

    def guardar(self):
        if not self.ruta:
            return self.guardar_como()
        try:
            motor.guardar(self.lz.img, self.ruta)
        except Exception as e:
            QMessageBox.warning(self, "Error", f"No se pudo guardar:\n{e}")
            return False
        self.lz.modificado = False
        self._estado()
        return True

    def guardar_como(self):
        f, _ = QFileDialog.getSaveFileName(self, "Guardar como", "imagen.png", FILTRO)
        if not f:
            return False
        self.ruta = f if Path(f).suffix else f + ".png"
        return self.guardar()

    def closeEvent(self, e):
        if self._descartar():
            ia.detener_todas()
            e.accept()
        else:
            e.ignore()

    # ------------------------------------------------------------ IA
    def _ia(self, texto, fn, fin):
        if self.tarea and self.tarea.isRunning():
            return
        self.l_ia.setText(texto)
        for b in (self.b_fondo, self.b_boc):
            b.setEnabled(False)
        self.tarea = ia.Tarea(lambda cancelar, emitir: fn())
        self.tarea.lista.connect(fin)
        self.tarea.fallo.connect(lambda m: self.l_ia.setText("Error: " + m))
        self.tarea.finished.connect(lambda: [b.setEnabled(True) for b in (self.b_fondo, self.b_boc)])
        self.tarea.start()

    def ia_fondo(self):
        img = motor.a_pil(self.lz.img)  # copia tomada en el hilo de la interfaz

        def fin(r):
            self.lz.reemplazar(motor.a_qimage(r))
            self.l_ia.setText("Fondo eliminado (Ctrl+Z para deshacer)")
        self._ia("Quitando fondo…", lambda: vision.quitar_fondo(img), fin)

    def ia_boceto(self):
        img = motor.recorte_dibujo(self.lz.img)
        if img is None:
            self.l_ia.setText("Dibuje algo primero.")
            return
        self._ia("Reconociendo…", lambda: motor.clasificador.clasificar(img),
                 lambda r: self.l_ia.setText("Boceto: " + ", ".join(f"{n} {p:.0%}" for n, p in r)))


def main():
    app = QApplication(sys.argv)
    v = Ventana(sys.argv[1] if len(sys.argv) > 1 else None)
    v.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
