"""Sustituye las fotos mal etiquetadas usando taxon_id exacto (el criterio no mira las predicciones)."""
import csv, json, time
from pathlib import Path
import requests
D = Path(__file__).resolve().parent.parent / "evaluacion"
s = requests.Session()
s.mount("https://", requests.adapters.HTTPAdapter(max_retries=requests.packages.urllib3.util.Retry(total=4, backoff_factor=5)))
def tid(nombre, rango):
    if rango == "genero de":  # el nombre del género es ambiguo: se toma el padre de la especie
        return next(t["parent_id"] for t in s.get("https://api.inaturalist.org/v1/taxa", params=dict(q=nombre, rank="species"), timeout=60).json()["results"] if t["name"] == nombre)
    for t in s.get("https://api.inaturalist.org/v1/taxa", params=dict(q=nombre, rank=rango), timeout=60).json()["results"]:
        if t["name"] == nombre: return t["id"]
    raise SystemExit("sin taxon " + nombre)
malas = [m for m in json.load(open(D/"etiquetas_descartadas.json", encoding="utf8")) if m[2] != "Melanosuchus niger"]
filas = list(csv.DictReader(open(D/"creditos_fotos_test.csv", encoding="utf-8-sig")))
quitar = {m[0] for m in malas}
for q in quitar: (D/"fauna_test"/q).unlink(missing_ok=True)
filas = [f for f in filas if f["archivo"] not in quitar]
acred = {f["archivo"] for f in filas}
for x in (D/"fauna_test").glob("*/*.jpg"):
    if f"{x.parent.name}/{x.name}" not in acred: x.unlink()
usadas = {f["url"] for f in filas} | {f["url"] for f in csv.DictReader(open(D/"creditos_fotos.csv", encoding="utf-8-sig"))}
for clase, nombre, rango in (("caimán", "Caiman", "genus"), ("guacamayo", "Ara macao", "genero de"), ("perezoso", "Bradypus", "genus"), ("rana", "Dendrobatidae", "family")):
    falta = 5 - len(list((D/"fauna_test"/clase).glob("*.jpg")))
    r = s.get("https://api.inaturalist.org/v1/observations", params=dict(taxon_id=tid(nombre, rango), quality_grade="research", photo_license="cc0,cc-by", per_page=20, order_by="votes"), timeout=60).json()
    for o in r["results"]:
        p = o["photos"][0]
        if falta <= 0 or o["uri"] in usadas or not p.get("license_code"): continue
        d = D/"fauna_test"/clase; d.mkdir(exist_ok=True); f = d/f"{p['id']}.jpg"
        f.write_bytes(s.get(p["url"].replace("square", "medium"), timeout=60).content)
        filas.append(dict(archivo=f"{clase}/{f.name}", licencia=p["license_code"], atribucion=p["attribution"], url=o["uri"])); falta -= 1
        print(clase, o["taxon"]["name"])
    time.sleep(1)
with open(D/"creditos_fotos_test.csv", "w", newline="", encoding="utf-8-sig") as f:
    w = csv.DictWriter(f, ["archivo", "licencia", "atribucion", "url"]); w.writeheader(); w.writerows(filas)
