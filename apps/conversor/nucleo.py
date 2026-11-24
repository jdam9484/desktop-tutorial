"""Núcleo del conversor: cabeceras binarias, conversión y lotes con clasificación opcional."""
import csv
import struct
from pathlib import Path

from PIL import Image, ImageOps

from apps.comun.archivos import guardar_atomico

EXT = {"bmp": "BMP", "jpg": "JPEG", "png": "PNG", "gif": "GIF", "tif": "TIFF", "webp": "WEBP"}
LEE = {".bmp", ".jpg", ".jpeg", ".png", ".gif", ".tif", ".tiff", ".webp"}


def cabecera(ruta):
    """Identifica el formato por sus bytes mágicos (no por la extensión) y lee sus dimensiones."""
    with open(ruta, "rb") as f:
        b = f.read(64)
        d = dict(formato="desconocido", magico=b[:8].hex(" "), ancho=None, alto=None, bits=None)
        if b[:2] == b"BM" and len(b) >= 30:
            w, h, _, bits = struct.unpack("<iiHH", b[18:30])
            d.update(formato="BMP", ancho=w, alto=abs(h), bits=bits)
        elif b[:8] == b"\x89PNG\r\n\x1a\n":
            w, h, prof, tipo = struct.unpack(">IIBB", b[16:26])
            d.update(formato="PNG", ancho=w, alto=h, bits=prof * {0: 1, 2: 3, 3: 1, 4: 2, 6: 4}.get(tipo, 1))
        elif b[:6] in (b"GIF87a", b"GIF89a"):
            w, h, flags = struct.unpack("<HHB", b[6:11])
            d.update(formato="GIF", ancho=w, alto=h, bits=(flags & 7) + 1)
        elif b[:3] == b"\xff\xd8\xff":
            d["formato"] = "JPEG"
            f.seek(2)
            while True:  # recorre los segmentos hasta SOFn
                m = f.read(2)
                if len(m) < 2 or m[0] != 0xFF:
                    break
                if m[1] in range(0xC0, 0xD0) and m[1] not in (0xC4, 0xC8, 0xCC):
                    _, prof, h, w, comp = struct.unpack(">HBHHB", f.read(8))
                    d.update(ancho=w, alto=h, bits=prof * comp)
                    break
                largo = struct.unpack(">H", f.read(2))[0]
                f.seek(largo - 2, 1)
        elif b[:4] in (b"II*\0", b"MM\0*"):
            d["formato"] = "TIFF"
            o = "<" if b[:2] == b"II" else ">"
            f.seek(struct.unpack(o + "I", b[4:8])[0])
            n = struct.unpack(o + "H", f.read(2))[0]
            for _ in range(n):
                tag, tipo, cnt, val = struct.unpack(o + "HHI4s", f.read(12))
                num = struct.unpack(o + "H", val[:2])[0] if tipo == 3 else struct.unpack(o + "I", val)[0]
                if tag == 256:
                    d["ancho"] = num
                elif tag == 257:
                    d["alto"] = num
                elif tag == 277:
                    d["bits"] = 8 * num
        elif b[:4] == b"RIFF" and b[8:12] == b"WEBP":
            d["formato"] = "WEBP"
            with Image.open(ruta) as im:
                d.update(ancho=im.width, alto=im.height, bits=8 * len(im.getbands()))
    return d


def abrir(ruta):
    with Image.open(ruta) as im:
        im.load()
        return ImageOps.exif_transpose(im)


def guardar(img, ruta, calidad=80):
    fmt = EXT.get(Path(ruta).suffix.lower().lstrip(".").replace("jpeg", "jpg").replace("tiff", "tif"))
    if not fmt:
        raise ValueError("Formato de salida no soportado")
    if fmt in ("JPEG", "BMP"):
        if img.mode in ("RGBA", "LA", "P", "PA"):
            rgba = img.convert("RGBA")
            plano = Image.new("RGB", img.size, "white")
            plano.paste(rgba, mask=rgba.getchannel("A"))
            img = plano
        elif img.mode not in ("RGB", "L"):
            img = img.convert("RGB")
    op = {"JPEG": dict(quality=calidad, subsampling="4:2:0"), "WEBP": dict(quality=calidad),
          "TIFF": dict(compression="raw")}.get(fmt, {})
    guardar_atomico(ruta, lambda t: img.save(t, fmt, **op))


def redimensionar(img, ancho=0, alto=0):
    """Lanczos manteniendo proporción; 0 = libre."""
    if not ancho and not alto:
        return img
    k = min(ancho / img.width if ancho else 1e9, alto / img.height if alto else 1e9)
    return img.resize((max(1, round(img.width * k)), max(1, round(img.height * k))), Image.LANCZOS)


def lote(archivos, carpeta, ext, ancho=0, alto=0, calidad=80, clasificador=None, umbral=0.4, cancelar=None,
         avance=None):
    """Convierte todo; si hay clasificador, ordena por especie y escribe clasificacion.csv. Un error no detiene el lote."""
    carpeta = Path(carpeta)
    filas = []
    for i, a in enumerate(archivos, 1):
        if cancelar is not None and cancelar.is_set():
            break
        a = Path(a)
        fila = dict(archivo=a.name, salida="", especie="", confianza="", error="")
        try:
            img = abrir(a)
            destino = carpeta
            if clasificador:
                n, p = clasificador.clasificar(img, 1)[0]
                fila.update(especie=n, confianza=f"{p:.3f}")
                destino = carpeta / (n if p >= umbral else "sin clasificar")
            destino.mkdir(parents=True, exist_ok=True)
            s = destino / f"{a.stem}.{ext}"
            k = 1
            while s.exists():  # nunca sobrescribe
                s = destino / f"{a.stem}_{k}.{ext}"
                k += 1
            guardar(redimensionar(img, ancho, alto), s, calidad)
            fila["salida"] = str(s.relative_to(carpeta))
        except Exception as e:
            fila["error"] = f"{type(e).__name__}: {e}"
        filas.append(fila)
        if avance:
            avance((i, len(archivos), fila))
    if clasificador and filas:
        carpeta.mkdir(parents=True, exist_ok=True)
        with open(carpeta / "clasificacion.csv", "w", newline="", encoding="utf-8-sig") as f:
            w = csv.DictWriter(f, filas[0].keys())
            w.writeheader()
            w.writerows(filas)
    return filas
