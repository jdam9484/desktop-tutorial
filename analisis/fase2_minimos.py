"""Fase 2: crea los archivos minimos CON los originales y registra modulos y archivos abiertos."""
import sys, os, subprocess, time, json, shutil
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from ui_tools import *
R = Path(__file__).resolve().parent.parent; H = R/"herramientas"; M = R/"muestras"
PDF = next(R.glob("Guia*.pdf"))
def rutas(pid, d):
    p = psutil.Process(pid)
    try: maps = sorted({m.path for m in p.memory_maps()})
    except Exception as e: maps = [f"error {e}"]
    try: of = sorted({f.path for f in p.open_files()})
    except Exception as e: of = [f"error {e}"]
    json.dump(dict(modulos=maps, abiertos=of), open(d/"es_rutas.json", "w", encoding="utf8"), indent=1, ensure_ascii=False)
    print(d.name, "modulos/mapeos:", len(maps), "abiertos:", len(of))
def A():
    sb = H/"openoffice/program"
    subprocess.Popen([str(sb/"soffice.exe"), "-headless", "-nologo", "-norestore", "-nofirststartwizard",
                      "-accept=socket,host=127.0.0.1,port=2099;urp;"])
    q = subprocess.Popen([str(sb/"python.exe"), str(R/"analisis/uno_minimo.py"), str(M/"minimo_writer")], env=dict(os.environ, PYTHONPATH=str(sb)))
    time.sleep(3)
    for p in psutil.process_iter(["name"]):
        if p.info["name"] == "soffice.bin": rutas(p.pid, R/"evidencias/A_writer")
    q.wait(60)
def B():
    from PIL import Image
    f = M/"minimo_paint.png"
    Image.new("RGB", (10, 10), (255, 0, 0)).save(f)   # rojo; Paint voltea y reescribe
    shutil.copy(f, M/"minimo_paint_entrada.png")
    subprocess.Popen(["mspaint.exe", str(f)])
    h = esperar_ventana(titulo="minimo_paint", t=20); time.sleep(3)
    w = auto.ControlFromHandle(h)
    w.ButtonControl(Name="Voltear").GetExpandCollapsePattern().Expand(); time.sleep(1)
    it = w.MenuItemControl(RegexName=".*orizontal.*")
    it.GetInvokePattern().Invoke(); time.sleep(1.5)
    rutas(win32process.GetWindowThreadProcessId(h)[1], R/"evidencias/B_paint")
    w.ButtonControl(Name="Guardar").GetInvokePattern().Invoke(); time.sleep(2)
    win32gui.PostMessage(h, win32con.WM_CLOSE, 0, 0)
def C():
    subprocess.Popen([str(H/"sumatra/SumatraPDF.exe"), str(PDF)])
    h = esperar_ventana(titulo="SumatraPDF"); time.sleep(2)
    rutas(win32process.GetWindowThreadProcessId(h)[1], R/"evidencias/C_sumatra")
    win32gui.PostMessage(h, win32con.WM_CLOSE, 0, 0)
def D():
    i = str(H/"irfanview/i_view64.exe")
    from PIL import Image
    Image.new("RGB", (10, 10), (255, 0, 0)).save(M/"rojo10.png")
    for e in ("bmp", "jpg", "gif", "tif", "png"):
        subprocess.run([i, str(M/"rojo10.png"), f"/convert={M/('minimo_irfan.'+e)}"], timeout=30)
    subprocess.Popen([i, str(M/"rojo10.png")]); time.sleep(2)
    h = esperar_ventana(titulo="IrfanView")
    rutas(win32process.GetWindowThreadProcessId(h)[1], R/"evidencias/D_irfanview")
    capturar(h, R/"evidencias/D_irfanview/ventana_original.png")
    win32gui.PostMessage(h, win32con.WM_CLOSE, 0, 0)
for n in (sys.argv[1:] or "ABCD"): 
    try: globals()[n]()
    except Exception as e: print(n, "ERROR", repr(e))
