"""Mide precisión y latencia de los módulos de IA. Resultados en evidencias/resultados/ia_final.json."""
import collections, json, os, sys, time
from pathlib import Path
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
R = Path(__file__).resolve().parent.parent; sys.path.insert(0, str(R))
from PIL import Image, ImageDraw
import numpy as np
from apps.comun import ia, vision
from apps.conversor.especies import clasificador as fauna
from apps.lienzo.motor import clasificador as bocetos
from apps.lector import rag
res = {}
def medir(pares, clf):
    ok1 = ok3 = 0; t = []; conf = collections.Counter(); por = collections.defaultdict(list); pasa = bien_pasa = 0
    clf.preparar()
    for real, im in pares:
        t0 = time.perf_counter(); r = clf.clasificar(im, 3); t.append(time.perf_counter() - t0)
        ok = r[0][0] == real; ok1 += ok; ok3 += real in [n for n, _ in r]; por[real].append(ok)
        if r[0][1] >= .4: pasa += 1; bien_pasa += ok
        if not ok: conf[f"{real} -> {r[0][0]}"] += 1
    n = len(pares)
    return dict(n=n, top1=ok1/n, top3=ok3/n, ms=1000*float(np.median(t)), cobertura_umbral=pasa/n, precision_umbral=bien_pasa/max(pasa,1),
                por_clase={k: sum(v)/len(v) for k, v in por.items()}, errores=conf.most_common(8))
res["fauna"] = medir([(d.name, Image.open(f).convert("RGB")) for d in sorted((R/"evaluacion/fauna_test").iterdir()) for f in sorted(d.iterdir())], fauna)
def dibujar(tr):
    im = Image.new("RGB", (330, 330), "white"); d = ImageDraw.Draw(im)
    for xs, ys in tr: d.line([(x+35, y+35) for x, y in zip(xs, ys)], fill="black", width=5, joint="curve")
    return im
b = json.load(open(R/"evaluacion/bocetos_test.json", encoding="utf8"))
res["bocetos"] = medir([(k, dibujar(t)) for k, l in b.items() for t in l], bocetos)
t = []
for f in sorted((R/"evaluacion/fauna_test").glob("*/*.jpg"))[::9]:
    im = Image.open(f); t0 = time.perf_counter(); vision.quitar_fondo(im); t.append(time.perf_counter() - t0)
res["fondo"] = dict(n=len(t), s_primera=t[0], s_mediana=float(np.median(t[1:])))
# RAG: (pregunta, palabras que debe contener, página; None = debe negarse)
pdf = next(R.glob("Guia*.pdf")); pp, ff = rag.extraer(pdf)
t0 = time.time(); ind = rag.IndiceRAG(pp, filas=ff).construir(usar_cache=False); tidx = time.time() - t0
Q = [("¿Qué edición mínima de Python se requiere?", ["3.10"], 2), ("¿Cuánto tiempo se asigna a la Fase 2?", ["30"], 3),
     ("¿Qué enfoque técnico corresponde al editor gráfico?", ["lienzo|canvas"], 1), ("¿Qué módulo de IA le toca al procesador de texto?", ["corrector|resumen|autocompletado"], 1),
     ("¿Qué contiene la sección 6 del informe?", ["comparativ"], 4), ("¿Dónde se entrega el informe?", ["aula virtual|github"], 3),
     ("¿Qué tecnología se usa para acoplar la IA de forma asíncrona?", ["threading|asyncio"], 3), ("¿De qué tamaño es la imagen de prueba mínima sugerida?", ["10"], 3),
     ("¿Qué editor hexadecimal se menciona?", ["hxd"], 2), ("¿Cuál es el precio de la matrícula?", None, None), ("¿Qué nota sacó el estudiante?", None, None), ("¿Cuántos habitantes tiene Puerto Maldonado?", None, None)]
det, tt = [], []
for q, pal, pg in Q:
    t0 = time.time(); r = "".join(ind.responder(q)); tt.append(time.time() - t0); l = r.lower()
    if pal is None: ok = "no encuentro" in l; cita = None
    else: ok = all(any(a in l for a in p.split("|")) for p in pal) and "no encuentro" not in l; cita = pg in rag.citas(r)
    det.append(dict(q=q, r=r, ok=ok, cita_ok=cita, s=tt[-1]))
res["rag"] = dict(n=len(Q), aciertos=sum(d["ok"] for d in det), citas_ok=sum(d["cita_ok"] is True for d in det), con_cita=sum(p is not None for *_, p in Q), indexar_s=tidx, fragmentos=len(ind.frag), s_mediana=float(np.median(tt)), detalle=det)
# Corrector: frases con errores y su corrección mínima esperada
C = [("Nosotros fuimos haber la película.", ["a ver"]), ("Ahy un arbol muy alto en la plasa.", ["hay", "árbol", "plaza"]),
     ("El a comido mucho oy.", ["ha comido", "hoy"]), ("La casa de mis abuelo son grandes.", ["abuelos es grande"]),
     ("Dijistes que bendrias temprano.", ["dijiste ", "vendrías"]), ("Si yo tendria dinero viajaria.", ["tuviera", "viajaría"]),
     ("Mas sin embargo no lo iso.", ["sin embargo", "hizo"]), ("Hicieron mejor de lo que esperabamos.", ["esperábamos"])]
from apps.escritor.main import SISTEMA
det, tt = [], []
for s, esp in C:
    t0 = time.time()
    r = "".join(ia.chat([{"role": "system", "content": SISTEMA}, {"role": "user", "content": "Corrige ortografía, gramática y estilo sin cambiar el significado ni agregar información. Devuelve solo el texto corregido:\n\n" + s}], temperatura=.1, max_tokens=200))
    tt.append(time.time() - t0); det.append(dict(s=s, r=r, ok=sum(e in r.lower() for e in esp), de=len(esp)))
res["corrector"] = dict(corregidos=sum(d["ok"] for d in det), total=sum(d["de"] for d in det), s_mediana=float(np.median(tt)), detalle=det)
tt = []
for s in ("La Amazonía peruana es una región", "El objetivo de la ingeniería inversa es", "En conclusión, los resultados muestran que"):
    t0 = time.time(); r = "".join(ia.chat([{"role": "system", "content": "Continúas textos en español. Responde SOLO con la continuación inmediata (máximo 15 palabras), sin repetir lo escrito."}, {"role": "user", "content": s}], modelo=ia.MODELO_RAPIDO, max_tokens=40, temperatura=.3)); tt.append(time.time() - t0); print(s, "|", r)
res["autocompletar"] = dict(s_primera=tt[0], s_siguientes=float(np.mean(tt[1:])))
json.dump(res, open(R/"evidencias/resultados/ia_final.json", "w", encoding="utf8"), ensure_ascii=False, indent=1)
for k, v in res.items(): print(k, {a: b for a, b in v.items() if a != "detalle"})
for d in res["rag"]["detalle"] + res["corrector"]["detalle"]: print(d)
