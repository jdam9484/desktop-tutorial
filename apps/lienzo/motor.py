"""Motor del lienzo: conversión de imágenes, relleno, formas y guardado compatible con Paint."""
import math
from pathlib import Path

import numpy as np
from PIL import Image
from PyQt6.QtCore import QPointF, QRectF
from PyQt6.QtGui import QImage, QPainterPath, QPolygonF

from apps.comun.archivos import guardar_atomico
from apps.comun.vision import ZeroShot

FORMAS = ["Línea", "Elipse", "Rectángulo", "Rect. redondeado", "Triángulo", "Diamante", "Pentágono", "Hexágono",
          "Flecha", "Estrella"]
BOCETOS = {"casa": "house", "árbol": "tree", "sol": "sun", "gato": "cat", "perro": "dog", "pez": "fish",
           "pájaro": "bird", "flor": "flower", "carro": "car", "barco": "boat", "avión": "airplane",
           "bicicleta": "bicycle", "cara": "smiley face", "estrella": "star", "corazón": "heart",
           "manzana": "apple", "taza": "cup", "reloj": "clock", "llave": "key", "montaña": "mountain",
           "nube": "cloud", "paraguas": "umbrella", "lentes": "eyeglasses", "mariposa": "butterfly"}
clasificador = ZeroShot(BOCETOS, ["a simple line drawing of a {}", "a hand-drawn sketch of a {}", "a doodle of a {}"])


def a_pil(q):
    q = q.convertToFormat(QImage.Format.Format_RGBA8888)
    p = q.constBits()
    p.setsize(q.sizeInBytes())
    a = np.frombuffer(p, np.uint8).reshape(q.height(), q.bytesPerLine())[:, :q.width() * 4]
    return Image.fromarray(a.reshape(q.height(), q.width(), 4).copy(), "RGBA")


def a_qimage(img):
    img = img.convert("RGBA")
    return QImage(img.tobytes(), img.width, img.height, img.width * 4,
                  QImage.Format.Format_RGBA8888).copy().convertToFormat(QImage.Format.Format_ARGB32)


def rellenar(q, x, y, color, tolerancia=0):
    """Relleno por inundación (4-vecinos) por tramos horizontales."""
    if not (0 <= x < q.width() and 0 <= y < q.height()):
        return q
    a = np.asarray(a_pil(q)).copy()
    nuevo = np.array(color.getRgb(), np.uint8)
    dif = np.abs(a.astype(np.int16) - a[y, x].astype(np.int16)).max(2) <= tolerancia
    visto = np.zeros(dif.shape, bool)
    pila, (h, w) = [(x, y)], dif.shape
    while pila:
        cx, cy = pila.pop()
        if visto[cy, cx] or not dif[cy, cx]:
            continue
        i = j = cx
        while i > 0 and dif[cy, i - 1] and not visto[cy, i - 1]:
            i -= 1
        while j < w - 1 and dif[cy, j + 1] and not visto[cy, j + 1]:
            j += 1
        visto[cy, i:j + 1] = True
        for ny in (cy - 1, cy + 1):
            if 0 <= ny < h:
                t = dif[ny, i:j + 1] & ~visto[ny, i:j + 1]
                ini = np.flatnonzero(t & ~np.r_[False, t[:-1]])
                pila.extend((i + int(k), ny) for k in ini)
    a[visto] = nuevo
    return a_qimage(Image.fromarray(a, "RGBA"))


def _poli(r, n, giro=-90):
    c = r.center()
    return QPolygonF([QPointF(c.x() + r.width() / 2 * math.cos(math.radians(giro + 360 * i / n)),
                              c.y() + r.height() / 2 * math.sin(math.radians(giro + 360 * i / n))) for i in range(n)])


def trazo_forma(nombre, a, b):
    p = QPainterPath()
    r = QRectF(a, b).normalized()
    if nombre == "Línea":
        p.moveTo(a)
        p.lineTo(b)
        return p
    if nombre == "Elipse":
        p.addEllipse(r)
        return p
    if nombre == "Rectángulo":
        p.addRect(r)
        return p
    if nombre == "Rect. redondeado":
        k = min(r.width(), r.height()) * .2
        p.addRoundedRect(r, k, k)
        return p
    x, y, w, h = r.x(), r.y(), r.width(), r.height()
    f = lambda pts: QPolygonF([QPointF(x + u * w, y + v * h) for u, v in pts])
    if nombre == "Triángulo":
        g = f([(.5, 0), (1, 1), (0, 1)])
    elif nombre == "Diamante":
        g = f([(.5, 0), (1, .5), (.5, 1), (0, .5)])
    elif nombre == "Flecha":
        g = f([(0, .3), (.6, .3), (.6, 0), (1, .5), (.6, 1), (.6, .7), (0, .7)])
    elif nombre == "Estrella":
        c = r.center()
        g = QPolygonF([QPointF(c.x() + w / 2 * (1 if i % 2 == 0 else .4) * math.cos(math.radians(-90 + 36 * i)),
                               c.y() + h / 2 * (1 if i % 2 == 0 else .4) * math.sin(math.radians(-90 + 36 * i)))
                       for i in range(10)])
    else:
        g = _poli(r, {"Pentágono": 5, "Hexágono": 6}[nombre])
    p.addPolygon(g)
    p.closeSubpath()
    return p


def abrir(ruta):
    with Image.open(ruta) as im:
        im.load()
        return a_qimage(im)


def guardar(q, ruta):
    """PNG RGBA con pHYs (como Paint); JPG y BMP se aplanan sobre blanco."""
    ext = Path(ruta).suffix.lower()
    img = a_pil(q)

    def escribir(t):
        if ext == ".png":
            img.save(t, "PNG", dpi=(120, 120))
            return
        plano = Image.new("RGB", img.size, "white")
        plano.paste(img, mask=img.getchannel("A"))
        if ext in (".jpg", ".jpeg"):
            plano.save(t, "JPEG", quality=92)
        elif ext == ".bmp":
            plano.save(t, "BMP")
        elif ext == ".gif":
            plano.save(t, "GIF")
        else:
            raise ValueError(f"Formato no soportado: {ext or '(sin extensión)'}")
    guardar_atomico(ruta, escribir)


def recorte_dibujo(q):
    """Recorta lo dibujado sobre fondo blanco; None si el lienzo está vacío."""
    img = a_pil(q)
    plano = Image.new("RGB", img.size, "white")
    plano.paste(img, mask=img.getchannel("A"))
    a = np.asarray(plano)
    ys, xs = np.nonzero((a < 245).any(2))
    if len(xs) < 30:
        return None
    l, t, r, b = xs.min(), ys.min(), xs.max() + 1, ys.max() + 1
    lado = int(max(r - l, b - t) * 1.25)
    cuad = Image.new("RGB", (lado, lado), "white")
    cuad.paste(plano.crop((l, t, r, b)), ((lado - (r - l)) // 2, (lado - (b - t)) // 2))
    return cuad
