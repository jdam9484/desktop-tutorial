"""Modelos de visión locales en ONNX Runtime: CLIP ViT-B/32 (zero-shot) y U²-Net (fondo)."""
import functools

import numpy as np
from PIL import Image

from .archivos import MODELOS
from .ia import ErrorIA


@functools.lru_cache(None)
def _sesion(nombre):
    import onnxruntime as ort
    ruta = MODELOS / nombre
    if not ruta.exists():
        raise ErrorIA(f"Falta el modelo {nombre}. Ejecute: python descargar_modelos.py")
    return ort.InferenceSession(str(ruta), providers=["CPUExecutionProvider"])


@functools.lru_cache(None)
def _tokenizador():
    from tokenizers import Tokenizer
    ruta = MODELOS / "clip_tokenizer.json"
    if not ruta.exists():
        raise ErrorIA("Falta clip_tokenizer.json. Ejecute: python descargar_modelos.py")
    t = Tokenizer.from_file(str(ruta))
    t.enable_truncation(77)
    return t


def _norm(v):
    return v / np.linalg.norm(v, axis=-1, keepdims=True)


def emb_textos(textos):
    tok, s = _tokenizador(), _sesion("clip_text_model.onnx")
    salida = []
    for t in textos:  # de uno en uno: evita el relleno
        ids = np.array([tok.encode(t).ids], dtype=np.int64)
        ent = {"input_ids": ids}
        if any(i.name == "attention_mask" for i in s.get_inputs()):
            ent["attention_mask"] = np.ones_like(ids)
        salida.append(s.run(["text_embeds"], ent)[0][0])
    return _norm(np.array(salida))


def emb_imagen(img):
    s = _sesion("clip_vision_model.onnx")
    img = img.convert("RGB")
    w, h = img.size
    k = 224 / min(w, h)
    img = img.resize((max(224, round(w * k)), max(224, round(h * k))), Image.BICUBIC)
    izq, arr = (img.width - 224) // 2, (img.height - 224) // 2
    a = np.asarray(img.crop((izq, arr, izq + 224, arr + 224)), np.float32) / 255
    a = (a - [0.48145466, 0.4578275, 0.40821073]) / [0.26862954, 0.26130258, 0.27577711]
    x = a.transpose(2, 0, 1)[None].astype(np.float32)
    return _norm(s.run(["image_embeds"], {"pixel_values": x})[0])[0]


class ZeroShot:
    """Clasificador zero-shot: promedia varias plantillas por etiqueta."""

    def __init__(self, clases, plantillas):
        self.clases, self.plantillas, self._t = clases, plantillas, None

    def preparar(self):
        if self._t is None:
            self._t = _norm(np.array([emb_textos([p.format(en) for p in self.plantillas]).mean(0)
                                      for en in self.clases.values()]))
        return self._t

    def clasificar(self, img, k=5):
        z = 100 * (self.preparar() @ emb_imagen(img))
        p = np.exp(z - z.max())
        p /= p.sum()
        nombres = list(self.clases)
        return [(nombres[i], float(p[i])) for i in np.argsort(-p)[:k]]


def quitar_fondo(img, modelo="u2net.onnx"):
    """Devuelve la imagen RGBA con la máscara de U²-Net en el canal alfa."""
    s = _sesion(modelo)
    rgb = img.convert("RGB")
    a = np.asarray(rgb.resize((320, 320), Image.LANCZOS), np.float32)
    a = a / max(float(a.max()), 1e-6)
    a = (a - [0.485, 0.456, 0.406]) / [0.229, 0.224, 0.225]
    d = s.run(None, {s.get_inputs()[0].name: a.transpose(2, 0, 1)[None].astype(np.float32)})[0][0, 0]
    if d.max() - d.min() < 1e-6:
        raise ErrorIA("No se distingue ningún objeto en la imagen.")
    d = (d - d.min()) / (d.max() - d.min()) * 255
    m = Image.fromarray(d.astype(np.uint8)).resize(rgb.size, Image.LANCZOS)
    res = img.convert("RGBA")
    alfa = np.minimum(np.asarray(m), np.asarray(res.getchannel("A")))
    res.putalpha(Image.fromarray(alfa))
    return res
