"""Interoperabilidad y rendimiento: original frente a réplica."""
import json, os, subprocess, sys, time
from pathlib import Path
R = Path(__file__).resolve().parent.parent; sys.path[:0] = [str(R), str(R/"analisis")]
from ui_tools import *
import numpy as np
H = R/"herramientas"; OUT = R/"evidencias/resultados"; I = R/"muestras/replica"; I.mkdir(exist_ok=True)
PDF = next(R.glob("Guia*.pdf")); PY = str(R/".venv/Scripts/python.exe"); res = {}
# ---- generar archivos con las réplicas
os.environ["QT_QPA_PLATFORM"] = "offscreen"
from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QTextDocument, QFont, QImage, QColor
from PyQt6.QtCore import Qt
app = QApplication([])
from apps.escritor import formatos
from apps.lienzo import motor
from apps.conversor import nucleo
from PIL import Image
HTML = "<h1>Titulo</h1><p>Hola <b>negrita</b> <i>cursiva</i> <u>sub</u> <span style='font-size:18pt'>grande</span></p><p align='center'>centro</p><ul><li>uno</li><li>dos</li></ul><ol><li>a</li></ol><p>fin</p>"
d = QTextDocument(); d.setDefaultFont(QFont("Times New Roman", 12)); d.setHtml(HTML)
for e in ("odt", "docx"): formatos.guardar(d, I/f"escritor.{e}")
q = QImage(37, 23, QImage.Format.Format_ARGB32); q.fill(QColor("red"))
for e in ("png", "bmp", "jpg"): motor.guardar(q, I/f"lienzo.{e}")
foto = sorted((R/"evaluacion/fauna").glob("*/*.jpg"))[0]
for e in nucleo.EXT: nucleo.guardar(nucleo.abrir(foto), I/f"conv.{e}")
# ---- A: Writer abre lo de la réplica (sin ventana)
sb = H/"openoffice/program"
subprocess.Popen([str(sb/"soffice.exe"), "-headless", "-nologo", "-norestore", "-nofirststartwizard", "-accept=socket,host=127.0.0.1,port=2099;urp;"])
try:
    subprocess.run([str(sb/"python.exe"), str(R/"analisis/uno_abrir.py"), str(OUT/"writer_abre.json"), str(I/"escritor.odt"), str(I/"escritor.docx")], env=dict(os.environ, PYTHONPATH=str(sb)), timeout=90)
    res["A_writer_abre"] = json.load(open(OUT/"writer_abre.json"))
    for _ in range(40):  # esperar a que el Writer sin ventana termine
        if not any(p.info["name"] == "soffice.bin" for p in psutil.process_iter(["name"])): break
        time.sleep(.5)
except Exception as ex: res["A_writer_abre"] = repr(ex)
print("A", json.dumps(res["A_writer_abre"], ensure_ascii=False)[:1800])
# ---- B: Paint abre lo de la réplica
res["B_paint_abre"] = {}
for e in ("png", "bmp", "jpg"):
    subprocess.Popen(["mspaint.exe", str(I/f"lienzo.{e}")])
    h = esperar_ventana(titulo="lienzo", clase="MSPaintApp", t=20); time.sleep(2.5)
    txt = [f["nombre"] for f in arbol(h, 30) if "xeles" in f["nombre"]] if h else []
    res["B_paint_abre"][e] = txt
    if h: win32gui.PostMessage(h, win32con.WM_CLOSE, 0, 0)
    time.sleep(1.5)
print("B", res["B_paint_abre"])
# ---- D: IrfanView lee lo de la réplica
res["D_irfan_abre"] = {}
iv = str(H/"irfanview/i_view64.exe")
for e in nucleo.EXT:
    t = OUT/f"info_{e}.txt"
    try:
        subprocess.run([iv, str(I/f"conv.{e}"), f"/info={t}", "/killmesoftly"], timeout=20)
        s = t.read_text(encoding="utf-16" if t.read_bytes()[:2] in (b"\xff\xfe", b"\xfe\xff") else "cp1252", errors="replace"); t.unlink()
        res["D_irfan_abre"][e] = [l.strip() for l in s.splitlines() if l.startswith(("Image dimensions", "Compression", "Original colors"))]
    except Exception as ex: res["D_irfan_abre"][e] = repr(ex)
print("D", res["D_irfan_abre"])
# fidelidad: misma foto por ambos conversores
W, Hh = nucleo.abrir(foto).size; comp = {}
for e in ("png", "bmp", "tif", "jpg"):
    f = I/f"irfan.{e}"; subprocess.run([iv, str(foto), "/jpgq=80", f"/convert={f}"], timeout=30); time.sleep(.3)
    a, b = (np.asarray(nucleo.abrir(x).convert("RGB"), float) for x in (f, I/f"conv.{e}")); m = ((a-b)**2).mean()
    comp[e] = dict(psnr="idéntico" if m == 0 else round(10*np.log10(65025/m), 1), kb_irfan=round(f.stat().st_size/1024, 1), kb_replica=round((I/f"conv.{e}").stat().st_size/1024, 1))
res["D_fidelidad"] = comp; print(comp)
fs = sorted((R/"evaluacion/fauna").glob("*/*.jpg"))[:40]
t0 = time.time()
for f in fs: subprocess.run([iv, str(f), f"/convert={I/'t.png'}"], timeout=30)
ti = time.time() - t0; t0 = time.time()
for f in fs: nucleo.guardar(nucleo.abrir(f), I/"t2.png")
res["D_lote40_png_s"] = dict(irfan_proceso_por_archivo=round(ti, 2), replica=round(time.time()-t0, 2)); print(res["D_lote40_png_s"])
# ---- arranque y memoria, 3 repeticiones
env = {k: v for k, v in os.environ.items() if k != "QT_QPA_PLATFORM"}
def lanzar(cmd, titulo, n=3):
    ts, ms = [], []
    for _ in range(n):
        t0 = time.time(); subprocess.Popen(cmd, env=env, cwd=R); h = esperar_ventana(titulo=titulo, t=40)
        if not h: return None
        ts.append(time.time()-t0); time.sleep(3)
        ms.append(psutil.Process(win32process.GetWindowThreadProcessId(h)[1]).memory_info().private/2**20)
        if "UNAMAD" in titulo: capturar(h, R/f"evidencias/{titulo.split()[0]}_replica.png")
        win32gui.PostMessage(h, win32con.WM_CLOSE, 0, 0); time.sleep(2)
    return dict(arranque_s=round(float(np.median(ts)), 2), privada_mb=round(float(np.median(ms)), 1))
odt, png = str(R/"muestras/minimo_writer.odt"), str(R/"muestras/minimo_paint.png")
A = lambda n, f: [PY, "-W", "ignore", str(R/f"apps/{n}/main.py"), f]
P = {"A_original": ([str(sb/"soffice.exe"), "-nologo", "-norestore", "-nofirststartwizard", odt], "OpenOffice Writer"), "A_replica": (A("escritor", odt), "Escritor UNAMAD"),
     "B_original": (["mspaint.exe", png], "minimo_paint - Paint"), "B_replica": (A("lienzo", png), "Lienzo UNAMAD"),
     "C_original": ([str(H/"sumatra/SumatraPDF.exe"), str(PDF)], "SumatraPDF"), "C_replica": (A("lector", str(PDF)), "Lector UNAMAD"),
     "D_original": ([iv, str(foto)], "IrfanView"), "D_replica": (A("conversor", str(foto)), "Conversor UNAMAD")}
res["rendimiento"] = {}
for k, (c, t) in P.items():
    res["rendimiento"][k] = lanzar(c, t); print(k, res["rendimiento"][k])
json.dump(res, open(OUT/"comparativa.json", "w", encoding="utf8"), ensure_ascii=False, indent=1)
