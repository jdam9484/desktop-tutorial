"""Verifica con la API de iNaturalist que cada foto del conjunto de prueba pertenezca al taxón pedido."""
import csv, json, time
from pathlib import Path
import requests
import sys
sys.path.insert(0, str(Path(__file__).parent))
D = Path(__file__).resolve().parent.parent / "evaluacion"
src = (Path(__file__).parent / "descargar_evaluacion.py").read_text(encoding="utf8")
TAXA = eval(src[src.index("TAXA = ") + 7: src.index("QD = ")])
filas = list(csv.DictReader(open(D / "creditos_fotos_test.csv", encoding="utf-8-sig")))
ids = [f["url"].rsplit("/", 1)[1] for f in filas]
info = {}
for i in range(0, len(ids), 30):
    r = requests.get("https://api.inaturalist.org/v1/observations", params=dict(id=",".join(ids[i:i+30]), per_page=30), timeout=60).json()
    for o in r["results"]:
        anc = [a["name"] for a in o["taxon"].get("ancestors", [])]
        anc += [a["name"] for x in o.get("identifications", []) for a in (x.get("taxon") or {}).get("ancestors", []) if x.get("current")]
        info[str(o["id"])] = (o["taxon"]["name"], o["taxon"].get("iconic_taxon_name"), set(anc))
    time.sleep(1)
malas = []
for f, i in zip(filas, ids):
    pedido = TAXA[f["archivo"].split("/")[0]]; n, ico, anc = info[i]
    if not (n == pedido or n.startswith(pedido + " ") or pedido in anc): malas.append((f["archivo"], pedido, n, ico))
json.dump(malas, open(D / "etiquetas_descartadas.json", "w", encoding="utf8"), ensure_ascii=False, indent=1)
print(len(info), "verificadas; descartadas:", len(malas))
for m in malas: print(m)
