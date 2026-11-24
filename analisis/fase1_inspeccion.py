"""Fase 1: lanza cada original, captura ventana, árbol UIA, menús, memoria y arranque."""
import subprocess, sys, os, time, json
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from ui_tools import *
R = Path(__file__).resolve().parent.parent
H = R / "herramientas"
PDF = next(R.glob("Guia*.pdf"))
APPS = {
 "A_writer": dict(cmd=[str(H/"openoffice/program/soffice.exe"), "-writer", "-nologo", "-norestore", "-nofirststartwizard"], titulo="OpenOffice Writer", proc="soffice.bin"),
 "B_paint": dict(cmd=["mspaint.exe"], titulo="Paint", proc="mspaint.exe"),
 "C_sumatra": dict(cmd=[str(H/"sumatra/SumatraPDF.exe"), str(PDF)], titulo="SumatraPDF", proc="SumatraPDF.exe"),
 "D_irfanview": dict(cmd=[str(H/"irfanview/i_view64.exe")], titulo="IrfanView", proc="i_view64.exe"),
}
def main(cuales):
    for k in cuales:
        a = APPS[k]; d = R/"evidencias"/k
        ya = {p.pid for p in psutil.process_iter(["name"]) if p.info["name"] == a["proc"]}
        if ya: print(k, "YA ESTABA ABIERTO, no lo toco:", ya); continue
        t0 = time.time()
        subprocess.Popen(a["cmd"])
        h = esperar_ventana(titulo=a["titulo"], t=60)
        dt = time.time() - t0
        if not h: print(k, "sin ventana"); print(ventanas(titulo="")); continue
        time.sleep(5)
        pid = win32process.GetWindowThreadProcessId(h)[1]
        mem = psutil.Process(pid).memory_info()
        capturar(h, d/"ventana_original.png")
        filas = arbol(h); guardar_arbol(filas, str(d/"arbol_uia"))
        m = menu_win32(h)
        (d/"menu_win32.txt").write_text("\n".join("  "*x[0]+x[1]+(f"  [{x[2]}]" if x[2] else "") for x in m), encoding="utf8")
        info = dict(titulo=win32gui.GetWindowText(h), clase=win32gui.GetClassName(h), pid=pid,
                    proceso=psutil.Process(pid).name(), arranque_s=round(dt, 2),
                    rss_mb=round(mem.rss/2**20, 1), privada_mb=round(mem.private/2**20, 1),
                    nodos_uia=len(filas), items_menu=len(m))
        json.dump(info, open(d/"info.json", "w", encoding="utf8"), ensure_ascii=False, indent=1)
        print(k, info)
        win32gui.PostMessage(h, win32con.WM_CLOSE, 0, 0)
        time.sleep(2)
main(sys.argv[1:] or list(APPS))
