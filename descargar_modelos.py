"""Descarga los modelos ONNX (no se versionan por su tamaño)."""
import urllib.request
from pathlib import Path

CLIP = "https://huggingface.co/Xenova/clip-vit-base-patch32/resolve/main/"
REMBG = "https://github.com/danielgatis/rembg/releases/download/v0.0.0/"
DESTINO = Path(__file__).parent / "modelos"
DESTINO.mkdir(exist_ok=True)
for nombre, url in {
    "clip_vision_model.onnx": CLIP + "onnx/vision_model.onnx",
    "clip_text_model.onnx": CLIP + "onnx/text_model.onnx",
    "clip_tokenizer.json": CLIP + "tokenizer.json",
    "u2net.onnx": REMBG + "u2net.onnx",
}.items():
    if not (DESTINO / nombre).exists():
        print("Descargando", nombre)
        urllib.request.urlretrieve(url, DESTINO / nombre)
