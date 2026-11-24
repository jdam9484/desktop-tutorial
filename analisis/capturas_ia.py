"""Capturas de las réplicas con su módulo de IA en funcionamiento (datos reales, sin retoque)."""
import sys, time, json
from pathlib import Path
R = Path(__file__).resolve().parent.parent; sys.path.insert(0, str(R))
from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QPainter, QPen, QColor, QPolygon
from PyQt6.QtCore import QPoint, Qt
app = QApplication([]); E = R/"evidencias"
def esperar(obj, t=120):
    f = time.time()+t
    while time.time() < f and obj.tarea and obj.tarea.isRunning(): app.processEvents(); time.sleep(.02)
    for _ in range(20): app.processEvents(); time.sleep(.02)
def foto(w, n): app.processEvents(); w.grab().save(str(E/n)); w.hide()
from apps.escritor.main import Escritor
e = Escritor(); e.show()
e.ed.setHtml("<h1>La selva de Madre de Dios</h1><p>El rio Tambopata esta muy cresido y los niño juega en la orilla. Nose si podremos hir mañana a la reserva, pero me gustaria <b>ver guacamayos</b>.</p>")
e.ed.selectAll(); e.ia_corregir(); esperar(e); foto(e, "A_writer/replica_ia.png"); e.ed.document().setModified(False)
from apps.lienzo.main import Ventana
v = Ventana(); v.show(); b = json.load(open(R/"evaluacion/bocetos_test.json", encoding="utf8"))["gato"][0]
p = QPainter(v.lz.img); p.setPen(QPen(QColor("black"), 5))
for xs, ys in b: p.drawPolyline(QPolygon([QPoint(380+x, 220+y) for x, y in zip(xs, ys)]))
p.end(); v.ia_boceto(); esperar(v); foto(v, "B_paint/replica_boceto.png")
f = sorted((R/"evaluacion/fauna_test/jaguar").iterdir())[0]
v.abrir(str(f)); v.zoom.setValue(110); v.ia_fondo(); esperar(v); foto(v, "B_paint/replica_fondo.png"); v.lz.modificado = False
from apps.lector.main import Lector
l = Lector(next(R.glob("Guia*.pdf")), config=R/"cache_rag/cfg_captura.json"); l.show(); app.processEvents()
for q in ("¿Qué módulo de IA pide la opción C?", "¿Qué está prohibido según la nota de ética?", "¿Cuál es el precio de la matrícula?"):
    l.preg.setText(q); l.preguntar(); esperar(l)
foto(l, "C_sumatra/replica_rag.png")
from apps.conversor.main import Visor, DialogoLote
c = Visor(str(sorted((R/"evaluacion/fauna_test/guacamayo").iterdir())[1])); c.show(); app.processEvents(); c.ajustar(); c.identificar(); esperar(c); foto(c, "D_irfanview/replica_especie.png")
fs = [x for d in sorted((R/"evaluacion/fauna_test").iterdir())[:9] for x in sorted(d.iterdir())[:1]]
d = DialogoLote(None, fs); d.ia.setChecked(True); d.dest.setText(str(R/"cache_rag/lote_demo")); d.show(); d.iniciar(); esperar(d); foto(d, "D_irfanview/replica_lote.png")
