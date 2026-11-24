"""Utilidades de caja negra: captura de ventanas, árbol UIA y menús Win32.

Usa Microsoft UI Automation (la misma API de Inspect.exe / Accessibility Insights)
y solo fotografía la ventana del programa estudiado, nunca el escritorio completo.
"""
import ctypes, time, json, sys
from ctypes import wintypes
ctypes.windll.shcore.SetProcessDpiAwareness(2)
import win32gui, win32ui, win32con, win32process
import psutil
import uiautomation as auto
from PIL import Image

auto.SetGlobalSearchTimeout(3)
user32 = ctypes.windll.user32


def ventanas(pids=None, titulo=None):
    res = []
    def cb(h, _):
        if not win32gui.IsWindowVisible(h):
            return
        t = win32gui.GetWindowText(h)
        _, pid = win32process.GetWindowThreadProcessId(h)
        if pids and pid not in pids:
            return
        if titulo and titulo.lower() not in t.lower():
            return
        res.append((h, t, win32gui.GetClassName(h), pid))
    win32gui.EnumWindows(cb, None)
    return res


def arbol_pids(pid):
    try:
        p = psutil.Process(pid)
        return {pid} | {c.pid for c in p.children(recursive=True)}
    except psutil.NoSuchProcess:
        return {pid}


def esperar_ventana(pid=None, titulo=None, clase=None, t=30):
    fin = time.time() + t
    while time.time() < fin:
        for v in ventanas(arbol_pids(pid) if pid else None, titulo):
            r = win32gui.GetWindowRect(v[0])
            if (r[2] - r[0]) > 200 and (not clase or clase in v[2]):
                return v[0]
        time.sleep(0.1)
    return None


def capturar(hwnd, ruta):
    l, t, r, b = win32gui.GetWindowRect(hwnd)
    w, h = r - l, b - t
    dc = win32gui.GetWindowDC(hwnd)
    mfc = win32ui.CreateDCFromHandle(dc)
    sdc = mfc.CreateCompatibleDC()
    bmp = win32ui.CreateBitmap()
    bmp.CreateCompatibleBitmap(mfc, w, h)
    sdc.SelectObject(bmp)
    user32.PrintWindow(hwnd, sdc.GetSafeHdc(), 2)
    info, bits = bmp.GetInfo(), bmp.GetBitmapBits(True)
    img = Image.frombuffer("RGB", (info["bmWidth"], info["bmHeight"]), bits, "raw", "BGRX", 0, 1)
    win32gui.DeleteObject(bmp.GetHandle()); sdc.DeleteDC(); mfc.DeleteDC()
    win32gui.ReleaseDC(hwnd, dc)
    img.save(ruta)
    return img


def arbol(hwnd, prof=12, maxn=1500):
    raiz = auto.ControlFromHandle(hwnd)
    filas = []
    def rec(c, d):
        if len(filas) >= maxn:
            return
        try:
            r = c.BoundingRectangle
            filas.append(dict(nivel=d, tipo=c.ControlTypeName.replace("Control", ""), nombre=(c.Name or "")[:80],
                              id=c.AutomationId, clase=c.ClassName, atajo=c.AcceleratorKey or c.AccessKey,
                              rect=[r.left, r.top, r.right, r.bottom]))
            if d < prof:
                for h in c.GetChildren():
                    rec(h, d + 1)
        except Exception:
            pass
    rec(raiz, 0)
    return filas


def guardar_arbol(filas, base):
    json.dump(filas, open(base + ".json", "w", encoding="utf8"), ensure_ascii=False, indent=1)
    with open(base + ".txt", "w", encoding="utf8") as f:
        for x in filas:
            f.write("  " * x["nivel"] + f"[{x['tipo']}] \"{x['nombre']}\" id={x['id']} clase={x['clase']}"
                    + (f" atajo={x['atajo']}" if x["atajo"] else "") + "\n")


def menu_win32(hwnd):
    """Lee la estructura completa de un menú Win32 clásico."""
    class MII(ctypes.Structure):
        _fields_ = [("cbSize", wintypes.UINT), ("fMask", wintypes.UINT), ("fType", wintypes.UINT),
                    ("fState", wintypes.UINT), ("wID", wintypes.UINT), ("hSubMenu", wintypes.HMENU),
                    ("hbmpChecked", wintypes.HBITMAP), ("hbmpUnchecked", wintypes.HBITMAP),
                    ("dwItemData", ctypes.c_void_p), ("dwTypeData", wintypes.LPWSTR),
                    ("cch", wintypes.UINT), ("hbmpItem", wintypes.HBITMAP)]
    user32.GetMenu.restype = wintypes.HMENU
    user32.GetMenu.argtypes = [wintypes.HWND]
    user32.GetSubMenu.restype = wintypes.HMENU
    user32.GetSubMenu.argtypes = [wintypes.HMENU, ctypes.c_int]
    user32.GetMenuItemCount.argtypes = [wintypes.HMENU]
    user32.GetMenuStringW.argtypes = [wintypes.HMENU, wintypes.UINT, wintypes.LPWSTR, ctypes.c_int, wintypes.UINT]
    out = []
    def rec(m, d):
        for i in range(max(0, user32.GetMenuItemCount(m))):
            b = ctypes.create_unicode_buffer(256)
            user32.GetMenuStringW(m, i, b, 256, 0x400)
            sub = user32.GetSubMenu(m, i)
            if b.value:
                txt, _, acc = b.value.partition("\t")
                out.append((d, txt.replace("&", ""), acc))
            if sub:
                rec(sub, d + 1)
    m = user32.GetMenu(hwnd)
    if m:
        rec(m, 0)
    return out
