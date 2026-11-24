"""Conversor UNAMAD: réplica funcional de IrfanView con clasificación de fauna y flora amazónica."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from PIL import Image, ImageOps
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QAction, QImage, QKeySequence, QPixmap
from PyQt6.QtWidgets import (QApplication, QCheckBox, QComboBox, QDialog, QFileDialog, QFormLayout, QHBoxLayout,
                             QLabel, QLineEdit, QListWidget, QMainWindow, QMessageBox, QProgressBar, QPushButton,
                             QScrollArea, QSpinBox, QVBoxLayout)

from apps.comun import ia
from apps.conversor import nucleo
from apps.conversor.especies import clasificador


class DialogoLote(QDialog):
    def __init__(self, padre, archivos=()):
        super().__init__(padre)
        self.setWindowTitle("Conversión por lotes")
        self.resize(760, 560)
        self.tarea = None
        l = QVBoxLayout(self)
        self.lista = QListWidget()
        self.lista.addItems([str(a) for a in archivos])
        l.addWidget(self.lista)
        h = QHBoxLayout()
        for t, f in (("Agregar…", self.agregar), ("Quitar", lambda: self.lista.takeItem(self.lista.currentRow())),
                     ("Vaciar", self.lista.clear)):
            b = QPushButton(t)
            b.clicked.connect(lambda _, f=f: f())
            h.addWidget(b)
        l.addLayout(h)
        fm = QFormLayout()
        self.ext = QComboBox()
        self.ext.addItems(list(nucleo.EXT))
        self.ext.setCurrentText("jpg")
        self.an, self.al, self.ca = QSpinBox(), QSpinBox(), QSpinBox()
        for s in (self.an, self.al):
            s.setRange(0, 20000)
            s.setSpecialValueText("sin cambio")
        self.ca.setRange(1, 100)
        self.ca.setValue(80)
        self.dest = QLineEdit(str(Path.home() / "Pictures" / "convertidas"))
        bd = QPushButton("…")
        bd.clicked.connect(self._carpeta)
        hd = QHBoxLayout()
        hd.addWidget(self.dest)
        hd.addWidget(bd)
        self.ia = QCheckBox("Clasificar por especie con IA y ordenar en subcarpetas")
        fm.addRow("Formato:", self.ext)
        fm.addRow("Ancho máx.:", self.an)
        fm.addRow("Alto máx.:", self.al)
        fm.addRow("Calidad:", self.ca)
        fm.addRow("Destino:", hd)
        fm.addRow(self.ia)
        l.addLayout(fm)
        self.bar = QProgressBar()
        l.addWidget(self.bar)
        self.log = QListWidget()
        l.addWidget(self.log)
        h2 = QHBoxLayout()
        self.b_ini = QPushButton("Iniciar lote")
        self.b_ini.clicked.connect(self.iniciar)
        b_det = QPushButton("Detener")
        b_det.clicked.connect(lambda: self.tarea and self.tarea.cancelar.set())
        h2.addWidget(self.b_ini)
        h2.addWidget(b_det)
        l.addLayout(h2)

    def agregar(self):
        fs, _ = QFileDialog.getOpenFileNames(self, "Agregar", "", "Imágenes (" +
                                             " ".join("*" + e for e in sorted(nucleo.LEE)) + ")")
        self.lista.addItems(fs)

    def _carpeta(self):
        d = QFileDialog.getExistingDirectory(self, "Destino", self.dest.text())
        if d:
            self.dest.setText(d)

    def iniciar(self):
        fs = [self.lista.item(i).text() for i in range(self.lista.count())]
        if not fs or (self.tarea and self.tarea.isRunning()):
            return
        self.log.clear()
        self.bar.setValue(0)
        self.b_ini.setEnabled(False)
        # los valores se leen aquí: los widgets no se tocan desde el hilo
        args = dict(carpeta=self.dest.text(), ext=self.ext.currentText(), ancho=self.an.value(), alto=self.al.value(),
                    calidad=self.ca.value(), clasificador=clasificador if self.ia.isChecked() else None)
        self.tarea = ia.Tarea(lambda c, e: nucleo.lote(fs, cancelar=c, avance=e, **args))

        def avance(m):
            i, n, f = m
            self.bar.setValue(100 * i // n)
            esp = f" [{f['especie']} {float(f['confianza']):.0%}]" if f["especie"] else ""
            self.log.addItem(f"{f['archivo']}{esp} -> {f['salida'] or 'ERROR ' + f['error']}")
        self.tarea.avance.connect(avance)
        self.tarea.fallo.connect(lambda m: self.log.addItem("ERROR " + m))
        self.tarea.finished.connect(lambda: self.b_ini.setEnabled(True))
        self.tarea.start()

    def closeEvent(self, e):
        if self.tarea and self.tarea.isRunning():
            self.tarea.cancelar.set()
            self.tarea.wait(5000)
        e.accept()


class Visor(QMainWindow):
    def __init__(self, ruta=None):
        super().__init__()
        self.resize(1000, 720)
        self.ruta, self.img, self.zoom, self.tarea, self.deshacer_img = None, None, None, None, None
        self.lbl = QLabel("Abra una imagen (O)")
        self.lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl.setStyleSheet("color:#aaa")
        self.sc = QScrollArea()
        self.sc.setWidget(self.lbl)
        self.sc.setWidgetResizable(True)
        self.sc.setStyleSheet("background:black")
        self.setCentralWidget(self.sc)
        self.l_info, self.l_ia = QLabel(), QLabel()
        self.statusBar().addWidget(self.l_info)
        self.statusBar().addPermanentWidget(self.l_ia)
        self._menus()
        self.setWindowTitle("Conversor UNAMAD")
        if ruta:
            self.abrir(ruta)

    def _menus(self):
        I = self._img
        for m, its in {
            "&Archivo": [("Abrir…", self.dlg_abrir, "O"), ("Guardar como…", self.guardar, "S"),
                         ("Conversión por lotes…", self.lotes, "B"), ("Salir", self.close, "Esc")],
            "&Editar": [("Deshacer", self.deshacer, "Ctrl+Z"), ("Copiar", self.copiar, "Ctrl+C")],
            "&Imagen": [("Información…", self.info, "I"), ("Girar izquierda", lambda: I(lambda i: i.rotate(90, expand=True)), "L"),
                        ("Girar derecha", lambda: I(lambda i: i.rotate(-90, expand=True)), "R"),
                        ("Voltear vertical", lambda: I(ImageOps.flip), "V"),
                        ("Voltear horizontal", lambda: I(ImageOps.mirror), "H"),
                        ("Redimensionar…", self.redim, "Ctrl+R"), ("Escala de grises", lambda: I(lambda i: i.convert("L")), "Ctrl+G"),
                        ("Negativo", lambda: I(lambda i: ImageOps.invert(i.convert("RGB"))), "Ctrl+Shift+N")],
            "&Ver": [("Siguiente", lambda: self.mover(1), "Space"), ("Anterior", lambda: self.mover(-1), "Backspace"),
                     ("Acercar", lambda: self._zoom(1.25), "+"), ("Alejar", lambda: self._zoom(.8), "-"),
                     ("Tamaño original", lambda: self._zoom(None), "Ctrl+H"), ("Ajustar a la ventana", self.ajustar, "F"),
                     ("Pantalla completa", lambda: self.showNormal() if self.isFullScreen() else self.showFullScreen(), "Return")],
            "IA": [("Identificar especie", self.identificar, "E")],
            "A&yuda": [("Acerca de", lambda: QMessageBox.information(
                self, "Acerca de", "Conversor UNAMAD\nRéplica funcional académica con IA local."), None)],
        }.items():
            menu = self.menuBar().addMenu(m)
            for t, f, k in its:
                a = QAction(t, self)
                if k:
                    a.setShortcut(QKeySequence(k))
                a.triggered.connect(lambda _, f=f: f())
                menu.addAction(a)

    def abrir(self, f):
        try:
            self.img = nucleo.abrir(f)
            self.cab = nucleo.cabecera(f)
        except Exception as e:
            QMessageBox.warning(self, "Error", f"No se pudo abrir:\n{e}")
            return
        self.ruta, self.zoom, self.deshacer_img = Path(f).resolve(), None, None
        self.hermanos = sorted(p for p in self.ruta.parent.iterdir() if p.suffix.lower() in nucleo.LEE)
        self.l_ia.clear()
        self.ajustar()

    def _pintar(self):
        if self.img is None:
            return
        q = self.img.convert("RGBA")
        im = QImage(q.tobytes(), q.width, q.height, q.width * 4, QImage.Format.Format_RGBA8888).copy()
        z = self.zoom or 1
        self.lbl.setPixmap(QPixmap.fromImage(im).scaled(max(1, int(q.width * z)), max(1, int(q.height * z)),
                                                        Qt.AspectRatioMode.KeepAspectRatio,
                                                        Qt.TransformationMode.SmoothTransformation))
        n = self.hermanos.index(self.ruta) + 1 if self.ruta in self.hermanos else 1
        self.l_info.setText(f"{q.width} x {q.height} x {self.cab['bits']} BPP   {n}/{len(self.hermanos)}   {z:.0%}   "
                            f"{self.ruta.stat().st_size / 1024:.1f} KB   {self.cab['formato']}")
        self.setWindowTitle(f"{self.ruta.name} - Conversor UNAMAD")

    def ajustar(self):
        if self.img:
            v = self.sc.viewport().size()
            self.zoom = min(1.0, v.width() / self.img.width, v.height() / self.img.height)
            self._pintar()

    def _zoom(self, k):
        if self.img:
            self.zoom = 1.0 if k is None else max(.02, min(16, (self.zoom or 1) * k))
            self._pintar()

    def _img(self, f):
        if self.img:
            self.deshacer_img = self.img
            self.img = f(self.img)
            self._pintar()

    def deshacer(self):
        if self.deshacer_img is not None:
            self.img, self.deshacer_img = self.deshacer_img, self.img
            self._pintar()

    def copiar(self):
        if self.lbl.pixmap():
            QApplication.clipboard().setPixmap(self.lbl.pixmap())

    def mover(self, d):
        if self.ruta and self.hermanos:
            i = self.hermanos.index(self.ruta) if self.ruta in self.hermanos else 0
            self.abrir(self.hermanos[(i + d) % len(self.hermanos)])

    def redim(self):
        from PyQt6.QtWidgets import QInputDialog
        if self.img:
            n, ok = QInputDialog.getInt(self, "Redimensionar", "Nuevo ancho:", self.img.width, 1, 20000)
            if ok:
                self._img(lambda i: nucleo.redimensionar(i, n))

    def info(self):
        if self.img:
            QMessageBox.information(self, "Información", "\n".join(f"{k}: {v}" for k, v in self.cab.items()))

    def dlg_abrir(self):
        f, _ = QFileDialog.getOpenFileName(self, "Abrir", "", "Imágenes (" +
                                           " ".join("*" + e for e in sorted(nucleo.LEE)) + ")")
        if f:
            self.abrir(f)

    def guardar(self):
        if not self.img:
            return
        f, _ = QFileDialog.getSaveFileName(self, "Guardar como", self.ruta.stem + ".jpg",
                                           ";;".join(f"{v} (*.{k})" for k, v in nucleo.EXT.items()))
        if f:
            try:
                nucleo.guardar(self.img, f)
            except Exception as e:
                QMessageBox.warning(self, "Error", str(e))

    def lotes(self):
        DialogoLote(self, self.hermanos if self.ruta else []).exec()

    def identificar(self):
        if not self.img or (self.tarea and self.tarea.isRunning()):
            return
        self.l_ia.setText("Identificando…")
        im = self.img.copy()
        self.tarea = ia.Tarea(lambda c, e: clasificador.clasificar(im, 3))
        self.tarea.lista.connect(lambda r: self.l_ia.setText("IA: " + ", ".join(f"{n} {p:.0%}" for n, p in r)))
        self.tarea.fallo.connect(lambda m: self.l_ia.setText("Error: " + m))
        self.tarea.start()

    def closeEvent(self, e):
        ia.detener_todas()
        e.accept()


def main():
    app = QApplication(sys.argv)
    v = Visor(sys.argv[1] if len(sys.argv) > 1 else None)
    v.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
