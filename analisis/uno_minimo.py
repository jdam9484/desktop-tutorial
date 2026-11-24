# Se ejecuta con el python de OpenOffice: crea el .odt minimo (palabra en negrita)
import uno, sys, time
from com.sun.star.beans import PropertyValue
dest = sys.argv[1]
local = uno.getComponentContext()
res = local.ServiceManager.createInstanceWithContext("com.sun.star.bridge.UnoUrlResolver", local)
for i in range(40):
    try:
        ctx = res.resolve("uno:socket,host=127.0.0.1,port=2099;urp;StarOffice.ComponentContext"); break
    except Exception:
        time.sleep(0.5)
desk = ctx.ServiceManager.createInstanceWithContext("com.sun.star.frame.Desktop", ctx)
doc = desk.loadComponentFromURL("private:factory/swriter", "_blank", 0, ())
t = doc.Text; c = t.createTextCursor()
t.insertString(c, "Hola ", False)
c.CharWeight = 150.0
t.insertString(c, "mundo", False)
c.CharWeight = 100.0
t.insertString(c, " UNAMAD", False)
def pv(n, v):
    p = PropertyValue(); p.Name = n; p.Value = v; return p
doc.storeToURL(uno.systemPathToFileUrl(dest + ".odt"), ())
doc.storeToURL(uno.systemPathToFileUrl(dest + ".rtf"), (pv("FilterName", "Rich Text Format"),))
doc.close(True)
try: desk.terminate()
except Exception: pass
