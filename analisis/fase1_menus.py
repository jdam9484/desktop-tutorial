"""Despliega los menus de Writer y SumatraPDF por teclado y los lee via UIA."""
import subprocess, sys, os
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from ui_tools import *
R = Path(__file__).resolve().parent.parent; H = R/"herramientas"
PDF = next(R.glob("Guia*.pdf"))
def popups(pid, excluir):
    out = []
    for h, t, c, p in ventanas():
        if p == pid and h != excluir: out.append((h, t, c))
    return out
def recolectar(hwnd):
    filas = []
    for f in arbol(hwnd, 6, 400):
        if f["tipo"] == "MenuItem" and f["nombre"]: filas.append((f["nombre"], f["atajo"]))
    return filas
def writer():
    subprocess.Popen([str(H/"openoffice/program/soffice.exe"), "-writer", "-nologo", "-norestore", "-nofirststartwizard"])
    h = esperar_ventana(titulo="OpenOffice Writer", t=40); time.sleep(4)
    pid = win32process.GetWindowThreadProcessId(h)[1]
    w = auto.ControlFromHandle(h); w.SetActive(); time.sleep(1)
    nombres = ["Archivo","Editar","Ver","Insertar","Formato","Tabla","Herramientas","Ventana","Ayuda"]
    out = []
    for n in nombres:
        try:
            m = w.MenuItemControl(Name=n, searchDepth=3)
            m.GetExpandCollapsePattern().Expand() if m.GetExpandCollapsePattern() else m.Click(simulateMove=False)
        except Exception as e:
            print(n, "expand err", e)
        time.sleep(0.8)
        its = []
        for hh, t, c in popups(pid, h): its += recolectar(hh)
        out.append((n, its)); print(n, len(its))
        if n == "Archivo":
            for hh, t, c in popups(pid, h): capturar(hh, R/"evidencias/A_writer/menu_archivo.png")
        auto.SendKeys("{Esc}{Esc}"); time.sleep(0.3)
    (R/"evidencias/A_writer/menus.txt").write_text("\n".join(n+"\n"+"\n".join(f"  {a}  [{b}]" if b else f"  {a}" for a,b in i) for n,i in out), encoding="utf8")
    win32gui.PostMessage(h, win32con.WM_CLOSE, 0, 0)
def sumatra():
    subprocess.Popen([str(H/"sumatra/SumatraPDF.exe"), str(PDF)])
    h = esperar_ventana(titulo="SumatraPDF"); time.sleep(2)
    pid = win32process.GetWindowThreadProcessId(h)[1]
    w = auto.ControlFromHandle(h); w.SetActive(); time.sleep(0.5)
    win32gui.PostMessage(h, win32con.WM_SYSCOMMAND, win32con.SC_KEYMENU, 0); time.sleep(1)
    print(popups(pid, h))
    for i in (104, 105):
        b = w.ButtonControl(AutomationId=str(i))
        if b.Exists(1):
            b.Click(simulateMove=False); time.sleep(1)
            print(i, popups(pid, h))
            for hh, t, c in popups(pid, h): print(recolectar(hh))
            for hh, t, c, p in ventanas():
                if c == "#32768": print("menu", recolectar(hh)); capturar(hh, R/"evidencias/C_sumatra/menu.png")
            auto.SendKeys("{Esc}{Esc}")
    # paleta de comandos Ctrl+K: lista todas las funciones
    w.SetActive(); auto.SendKeys("{Ctrl}k"); time.sleep(1.5)
    print("tras Ctrl+K", popups(pid, h))
    for hh, t, c in popups(pid, h): capturar(hh, R/"evidencias/C_sumatra/paleta.png")
    for hh, t, c in popups(pid, h) + [(h, "", "")]:
        l = [f["nombre"] for f in arbol(hh, 8, 1500) if f["tipo"] == "ListItem"]
        if l:
            print("paleta", len(l)); (R/"evidencias/C_sumatra/comandos.txt").write_text("\n".join(l), encoding="utf8")
    capturar(h, R/"evidencias/C_sumatra/paleta_comandos.png")
    auto.SendKeys("{Esc}")
    win32gui.PostMessage(h, win32con.WM_CLOSE, 0, 0)
for n in sys.argv[1:] or ["writer", "sumatra"]:
    try: globals()[n]()
    except Exception as e: print(n, "ERR", repr(e))
