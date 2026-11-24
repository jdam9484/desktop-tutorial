"""Descarga fotos CC0/CC-BY (iNaturalist) y bocetos CC-BY (Quick, Draw!) para evaluar los módulos de IA."""
import csv, json, time
from pathlib import Path
import requests
D = Path(__file__).resolve().parent.parent / "evaluacion"
TAXA = {"jaguar": "Panthera onca", "ronsoco": "Hydrochoerus hydrochaeris", "guacamayo": "Ara", "tucán": "Ramphastos",
        "perezoso": "Bradypus", "mono": "Saimiri", "caimán": "Caiman", "anaconda": "Eunectes", "lobo de río": "Pteronura brasiliensis",
        "tapir": "Tapirus terrestris", "águila harpía": "Harpia harpyja", "rana": "Dendrobatidae", "mariposa": "Morpho",
        "oso hormiguero": "Myrmecophaga tridactyla", "orquídea": "Cattleya", "heliconia": "Heliconia",
        "nenúfar gigante": "Victoria amazonica", "cacao": "Theobroma cacao", "palmera": "Mauritia flexuosa"}
QD = {"casa": "house", "árbol": "tree", "sol": "sun", "gato": "cat", "perro": "dog", "pez": "fish", "pájaro": "bird",
      "flor": "flower", "carro": "car", "barco": "sailboat", "avión": "airplane", "bicicleta": "bicycle", "cara": "smiley face",
      "estrella": "star", "manzana": "apple", "taza": "cup", "reloj": "clock", "llave": "key", "montaña": "mountain",
      "nube": "cloud", "paraguas": "umbrella", "lentes": "eyeglasses", "mariposa": "butterfly"}
s = requests.Session(); s.headers["User-Agent"] = "python-requests"
filas = []
for es, tx in TAXA.items():
    r = s.get("https://api.inaturalist.org/v1/observations", params=dict(taxon_name=tx, quality_grade="research", photo_license="cc0,cc-by", per_page=8, page=2, order_by="votes"), timeout=60).json()
    n = 0
    for o in r.get("results", []):
        p = o["photos"][0]
        if n == 5 or not p.get("license_code"): continue
        d = D / "fauna_test" / es; d.mkdir(parents=True, exist_ok=True)
        f = d / f"{p['id']}.jpg"
        f.write_bytes(s.get(p["url"].replace("square", "medium"), timeout=60).content)
        filas.append([f"{es}/{f.name}", p["license_code"], p["attribution"], o["uri"]]); n += 1
    print(es, n); time.sleep(1)
with open(D / "creditos_fotos_test.csv", "w", newline="", encoding="utf-8-sig") as f:
    w = csv.writer(f); w.writerow(["archivo", "licencia", "atribucion", "url"]); w.writerows(filas)
boc = {}
for es, en in QD.items():
    r = s.get(f"https://storage.googleapis.com/quickdraw_dataset/full/simplified/{en}.ndjson", headers={"Range": "bytes=0-90000"}, timeout=60)
    ds = [json.loads(l) for l in r.text.split("\n")[:-1]]
    boc[es] = [d["drawing"] for d in ds if d["recognized"]][20:30]
json.dump(boc, open(D / "bocetos_test.json", "w", encoding="utf8"))
print({k: len(v) for k, v in boc.items()})
