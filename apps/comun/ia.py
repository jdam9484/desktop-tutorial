"""Acceso a la IA local (Ollama) y ejecución en segundo plano para no bloquear la interfaz."""
import json
import threading

import requests
from PyQt6.QtCore import QThread, pyqtSignal

OLLAMA = "http://127.0.0.1:11434"
MODELO = "llama3.1:8b"
MODELO_RAPIDO = "llama3.2:3b"
MODELO_EMB = "bge-m3"


class ErrorIA(Exception):
    """Error presentable al usuario."""


def _post(ruta, datos, stream=False, timeout=180):
    try:
        r = requests.post(OLLAMA + ruta, json=datos, stream=stream, timeout=(5, timeout))
    except requests.ConnectionError:
        raise ErrorIA("No hay conexión con Ollama. Ábralo e inténtelo otra vez.")
    except requests.Timeout:
        raise ErrorIA("El modelo tardó demasiado en responder.")
    if r.status_code == 404:
        raise ErrorIA(f"Falta el modelo. Ejecute: ollama pull {datos.get('model')}")
    if not r.ok:
        raise ErrorIA(f"Ollama respondió {r.status_code}: {r.text[:200]}")
    return r


def chat(mensajes, modelo=MODELO, temperatura=0.2, max_tokens=700, ctx=4096, cancelar=None):
    """Generador: entrega la respuesta por trozos."""
    r = _post("/api/chat", dict(model=modelo, messages=mensajes, stream=True, keep_alive="10m",
                                options=dict(temperature=temperatura, num_predict=max_tokens, num_ctx=ctx)), True)
    try:
        for linea in r.iter_lines():
            if cancelar is not None and cancelar.is_set():
                return
            if linea:
                d = json.loads(linea)
                if d.get("error"):
                    raise ErrorIA(d["error"])
                yield d.get("message", {}).get("content", "")
    except requests.RequestException as e:
        raise ErrorIA(f"Se cortó la respuesta: {e}")
    finally:
        r.close()


def embeddings(textos, modelo=MODELO_EMB):
    # en CPU: así no desaloja de la VRAM al modelo de chat (evita recargarlo en cada pregunta)
    return _post("/api/embed", dict(model=modelo, input=list(textos), keep_alive="10m",
                                options=dict(num_gpu=0))).json()["embeddings"]


class Tarea(QThread):
    """Ejecuta `fn(cancelar, emitir)` en otro hilo. `emitir` manda avances a la interfaz."""
    avance = pyqtSignal(object)
    lista = pyqtSignal(object)
    fallo = pyqtSignal(str)
    _vivas = set()

    def __init__(self, fn):
        super().__init__()
        self.fn = fn
        self.cancelar = threading.Event()
        Tarea._vivas.add(self)
        self.finished.connect(self._fin)

    def _fin(self):
        Tarea._vivas.discard(self)

    def run(self):
        try:
            r = self.fn(self.cancelar, self.avance.emit)
            if not self.cancelar.is_set():
                self.lista.emit(r)
        except ErrorIA as e:
            self.fallo.emit(str(e))
        except Exception as e:  # cualquier fallo se informa, nunca cierra la aplicación
            self.fallo.emit(f"{type(e).__name__}: {e}")


def detener_todas(ms=3000):
    for t in list(Tarea._vivas):
        t.cancelar.set()
        t.wait(ms)
