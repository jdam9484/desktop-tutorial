"""Pruebas de caja negra y de regresión de las cuatro réplicas (no requieren GPU ni Ollama)."""
import os
import sys
import zipfile
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
R = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(R))
import numpy as np
import pytest
from PIL import Image
from PyQt6.QtCore import QElapsedTimer, QEventLoop, QPointF, Qt, QTimer
from PyQt6.QtGui import QColor, QFont, QImage, QTextDocument
from PyQt6.QtWidgets import QApplication

app = QApplication.instance() or QApplication([])
from apps.comun import ia
from apps.comun.archivos import guardar_atomico
from apps.conversor import nucleo
from apps.escritor import formatos, odt
from apps.lector import rag
from apps.lienzo import motor

HTML = ("<h1>Título</h1><p>Hola <b>negrita</b> <i>cursiva</i> <u>sub</u> <s>tach</s> "
        "<span style='color:#ff0000;font-size:18pt'>rojo</span></p>"
        "<p align='center'>centro</p><ul><li>uno</li><li>dos</li></ul><ol><li>a</li></ol><p>fin  doble</p>")


def _doc(html=HTML):
    d = QTextDocument()
    d.setDefaultFont(QFont("Times New Roman", 12))
    d.setHtml(html)
    return d


def _formatos(doc):
    """{texto: (negrita, cursiva, subrayado, tachado)}"""
    out, b = {}, doc.begin()
    while b.isValid():
        it = b.begin()
        while not it.atEnd():
            f = it.fragment().charFormat()
            for p in it.fragment().text().split():
                out[p] = (f.fontWeight() >= 700, f.fontItalic(), f.fontUnderline(), f.fontStrikeOut())
            it += 1
        b = b.next()
    return out


# ---------------------------------------------------------------- comunes
def test_guardado_atomico_conserva_original(tmp_path):
    f = tmp_path / "a.txt"
    f.write_text("bueno")

    def falla(t):
        Path(t).write_text("a medias")
        raise RuntimeError
    with pytest.raises(RuntimeError):
        guardar_atomico(f, falla)
    assert f.read_text() == "bueno" and len(list(tmp_path.iterdir())) == 1


def _esperar(t, ms=8000):
    l = QEventLoop()
    t.finished.connect(l.quit)
    QTimer.singleShot(ms, l.quit)
    if t.isRunning():
        l.exec()
    app.processEvents()


def test_ia_no_bloquea_interfaz():
    import time
    huecos, cron = [], QElapsedTimer()
    cron.start()
    tic = QTimer()
    tic.timeout.connect(lambda: huecos.append(cron.restart()))
    tic.start(10)
    t = ia.Tarea(lambda c, e: time.sleep(1))
    t.start()
    _esperar(t)
    tic.stop()
    assert len(huecos) > 20 and max(huecos) < 300


def test_ollama_apagado_da_mensaje(monkeypatch):
    monkeypatch.setattr(ia, "OLLAMA", "http://127.0.0.1:9")
    m = []
    t = ia.Tarea(lambda c, e: list(ia.chat([{"role": "user", "content": "x"}])))
    t.fallo.connect(m.append)
    t.start()
    _esperar(t)
    assert m and "Ollama" in m[0]


# ---------------------------------------------------------------- A
def test_odt_estructura_como_writer(tmp_path):
    f = tmp_path / "x.odt"
    odt.guardar(_doc(), f)
    with zipfile.ZipFile(f) as z:
        i = z.infolist()[0]
        assert i.filename == "mimetype" and i.compress_type == zipfile.ZIP_STORED
        assert z.read("mimetype").decode() == odt.MIME
        x = z.read("content.xml").decode()
    assert 'fo:font-weight="bold"' in x and "text:list" in x


def test_odt_ida_y_vuelta(tmp_path):
    f = tmp_path / "x.odt"
    a, b = _doc(), QTextDocument()
    odt.guardar(a, f)
    odt.abrir(f, b)
    assert b.toPlainText() == a.toPlainText()
    fb = _formatos(b)
    for p in ("negrita", "cursiva", "sub", "tach"):
        assert fb[p] == _formatos(a)[p]
    assert b.begin().blockFormat().headingLevel() == 1
    assert b.findBlockByNumber(2).blockFormat().alignment() & Qt.AlignmentFlag.AlignHCenter
    assert b.findBlockByNumber(3).textList() is not None
    assert b.findBlockByNumber(6).textList() is None


def test_odt_abre_el_minimo_del_original():
    d = QTextDocument()
    odt.abrir(R / "muestras/minimo_writer.odt", d)
    assert d.toPlainText() == "Hola mundo UNAMAD"
    f = _formatos(d)
    assert f["mundo"][0] and not f["Hola"][0] and not f["UNAMAD"][0]


@pytest.mark.parametrize("ext", ["docx", "html", "txt"])
def test_otros_formatos(tmp_path, ext):
    f = tmp_path / f"x.{ext}"
    a, b = _doc("<p>Uno <b>dos</b></p><p>tres ñandú</p>"), QTextDocument()
    formatos.guardar(a, f)
    formatos.abrir(f, b)
    assert b.toPlainText() == a.toPlainText()
    if ext != "txt":
        assert _formatos(b)["dos"][0]


def test_docx_conserva_fuente_base(tmp_path):
    import docx
    f = tmp_path / "b.docx"
    formatos.guardar(_doc("<p>hola</p>"), f)
    n = docx.Document(f).styles["Normal"].font
    assert n.size.pt == 12 and n.name == "Times New Roman"


def test_extension_desconocida(tmp_path):
    with pytest.raises(ValueError):
        formatos.guardar(_doc(), tmp_path / "x.zzz")


def test_candado(tmp_path):
    f = tmp_path / "d.odt"
    a, b = formatos.Candado(f), formatos.Candado(f)
    assert a.tomar() and not b.tomar()
    b.soltar()
    assert (tmp_path / ".~lock.d.odt#").exists()
    a.soltar()
    assert not (tmp_path / ".~lock.d.odt#").exists()


def test_zoom_no_altera_tamano_guardado(tmp_path):
    from apps.escritor.main import Escritor
    e = Escritor()
    e.ed.setPlainText("hola")
    e.zoom.setValue(150)
    e.ruta = str(tmp_path / "z.odt")
    assert e.guardar()
    x = zipfile.ZipFile(e.ruta).read("styles.xml").decode()
    assert 'fo:font-size="12pt"' in x


def test_autocompletado_acepta_y_descarta():
    from apps.escritor.main import Escritor
    from PyQt6.QtTest import QTest
    e = Escritor()
    e.show()
    e.ed.setPlainText("La Amazonía es")
    e.ed.moveCursor(e.ed.textCursor().MoveOperation.End)
    e._proponer("muy diversa")
    QTest.keyClick(e.ed, Qt.Key.Key_Escape)
    assert e.ed.toPlainText() == "La Amazonía es"
    e._proponer("muy diversa")
    QTest.keyClick(e.ed, Qt.Key.Key_Tab)
    assert e.ed.toPlainText() == "La Amazonía es muy diversa"
    e.ed.document().setModified(False)
    e.close()


def test_reemplazar_todo():
    from apps.escritor.main import Escritor
    e = Escritor()
    e.ed.setPlainText("a b a")
    assert e.reemplazar_todo("a", "aa") == 2 and e.ed.toPlainText() == "aa b aa"


# ---------------------------------------------------------------- B
def _lienzo(w=60, h=40):
    q = QImage(w, h, QImage.Format.Format_ARGB32)
    q.fill(Qt.GlobalColor.white)
    return q


def test_relleno_respeta_bordes():
    q = _lienzo()
    for x in range(60):
        q.setPixelColor(x, 20, QColor("black"))
    q = motor.rellenar(q, 5, 5, QColor("red"))
    assert q.pixelColor(59, 0) == QColor("red") and q.pixelColor(5, 20) == QColor("black")
    assert q.pixelColor(5, 30) == QColor("white")


def test_png_rgba_y_phys(tmp_path):
    f = tmp_path / "a.png"
    motor.guardar(_lienzo(), f)
    b = f.read_bytes()
    assert b[25] == 6 and b"pHYs" in b


@pytest.mark.parametrize("ext", ["png", "bmp", "jpg", "gif"])
def test_guardar_abrir_lienzo(tmp_path, ext):
    f = tmp_path / f"a.{ext}"
    motor.guardar(_lienzo(), f)
    assert (motor.abrir(f).width(), motor.abrir(f).height()) == (60, 40)


@pytest.mark.parametrize("n", motor.FORMAS)
def test_formas(n):
    r = motor.trazo_forma(n, QPointF(50, 60), QPointF(10, 10)).boundingRect()
    assert r.width() > 20 and r.height() > 20 and r.left() >= 9.9 and r.right() <= 50.1


def test_deshacer_rehacer():
    from apps.lienzo.main import Ventana
    v = Ventana()
    v.girar(90)
    assert v.lz.img.width() == 720
    v.lz.deshacer()
    assert v.lz.img.width() == 1152
    v.lz.rehacer()
    assert v.lz.img.width() == 720


def test_boceto_vacio():
    assert motor.recorte_dibujo(_lienzo()) is None


# ---------------------------------------------------------------- C
def test_fragmentos_por_pagina():
    fr = rag.fragmentar(["a " * 400, "", "b " * 10])
    assert {n for n, _ in fr} == {1, 3} and all(len(t.split()) <= rag.TAM for _, t in fr)


def test_pdf_sin_texto():
    with pytest.raises(ia.ErrorIA):
        rag.IndiceRAG(["", " "])


def test_busqueda_vectorial():
    emb = lambda ts: [[t.count("gato") + .01, t.count("perro") + .01] for t in ts]
    i = rag.IndiceRAG(["gato gato", "perro"], emb).construir(usar_cache=False)
    assert i.buscar("perro")[0][0] == 2


def test_citas():
    assert rag.citas("x [pág. 3] y [pag 5]") == [3, 5]


def test_lector_busca_gira_y_recuerda(tmp_path):
    from apps.lector.main import Lector
    pdf = next(R.glob("Guia*.pdf"))
    c = tmp_path / "c.json"
    l = Lector(pdf, config=c)
    l.show()
    app.processEvents()
    assert len(l.v.doc) == 5 and l.v.buscar("Inspect", False) == 3
    l.v.poner(rot=90)
    l.v.ir(3)
    assert l.v.pag() == 3
    l.close()
    l2 = Lector(pdf, config=c)
    l2.show()
    for _ in range(5):
        app.processEvents()
    assert l2.v.rot == 90 and l2.v.pag() == 3


# ---------------------------------------------------------------- D
@pytest.mark.parametrize("ext,fmt", [("bmp", "BMP"), ("jpg", "JPEG"), ("gif", "GIF"), ("tif", "TIFF"), ("png", "PNG")])
def test_cabeceras_del_original(ext, fmt):
    d = nucleo.cabecera(R / f"muestras/minimo_irfan.{ext}")
    assert (d["formato"], d["ancho"], d["alto"]) == (fmt, 10, 10)


def test_cabecera_ignora_extension(tmp_path):
    f = tmp_path / "falso.jpg"
    Image.new("RGB", (3, 4)).save(f, "PNG")
    assert nucleo.cabecera(f)["formato"] == "PNG"


@pytest.mark.parametrize("ext", list(nucleo.EXT))
def test_convertir(tmp_path, ext):
    f = tmp_path / f"a.{ext}"
    nucleo.guardar(Image.new("RGBA", (20, 10), (255, 0, 0, 128)), f)
    d = nucleo.cabecera(f)
    assert (d["ancho"], d["alto"]) == (20, 10) and d["formato"] == nucleo.EXT[ext]


def test_lote_no_se_detiene_ni_sobrescribe(tmp_path):
    a, mal = tmp_path / "a.png", tmp_path / "mal.png"
    Image.new("RGB", (100, 50), "red").save(a)
    mal.write_text("no soy imagen")
    sal = tmp_path / "out"
    r = nucleo.lote([a, mal, a], sal, "jpg", ancho=40)
    assert [bool(x["error"]) for x in r] == [False, True, False]
    assert nucleo.cabecera(sal / "a.jpg")["ancho"] == 40 and (sal / "a_1.jpg").exists()


def test_lote_clasificado(tmp_path):
    class C:
        def clasificar(self, im, k):
            return [("jaguar", .9)]
    a = tmp_path / "a.png"
    Image.new("RGB", (10, 10)).save(a)
    nucleo.lote([a], tmp_path / "o", "bmp", clasificador=C())
    assert (tmp_path / "o/jaguar/a.bmp").exists() and (tmp_path / "o/clasificacion.csv").exists()
