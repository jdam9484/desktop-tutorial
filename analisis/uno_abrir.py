# python de OpenOffice: abre los .odt/.docx de la replica en Writer y reporta texto y negritas
import uno, sys, time, json
from com.sun.star.beans import PropertyValue
L = uno.getComponentContext()
res = L.ServiceManager.createInstanceWithContext("com.sun.star.bridge.UnoUrlResolver", L)
for i in range(60):
    try:
        ctx = res.resolve("uno:socket,host=127.0.0.1,port=2099;urp;StarOffice.ComponentContext"); break
    except Exception: time.sleep(0.5)
desk = ctx.ServiceManager.createInstanceWithContext("com.sun.star.frame.Desktop", ctx)
def pv(n, v):
    p = PropertyValue(); p.Name = n; p.Value = v; return p
out = []
try:
  for f in sys.argv[2:]:
      doc = desk.loadComponentFromURL(uno.systemPathToFileUrl(f), "_blank", 0, (pv("Hidden", True),))
      d = {"archivo": f, "abre": doc is not None, "parrafos": []}
      if doc:
          e = doc.Text.createEnumeration()
          while e.hasMoreElements():
              p = e.nextElement()
              if not p.supportsService("com.sun.star.text.Paragraph"): continue
              ps = []; r = p.createEnumeration()
              while r.hasMoreElements():
                  t = r.nextElement()
                  if t.String: ps.append([t.String, t.CharWeight > 120, str(t.CharPosture.value) == "ITALIC", t.CharUnderline > 0, t.CharHeight])
              d["parrafos"].append([p.ParaStyleName, str(p.ParaAdjust), p.NumberingStyleName, ps])
          doc.close(True)
      out.append(d)
  open(sys.argv[1], "w").write(json.dumps(out))
finally:
  try: desk.terminate()
  except Exception: pass
