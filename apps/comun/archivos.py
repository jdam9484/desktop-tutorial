"""Escritura atómica: patrón deducido con Process Monitor en Writer y Paint (temporal + renombrado)."""
import os
import tempfile
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
MODELOS = RAIZ / "modelos"


def guardar_atomico(destino, escribir):
    """`escribir(ruta_tmp)` genera el contenido; solo si termina bien reemplaza al destino."""
    destino = Path(destino)
    fd, tmp = tempfile.mkstemp(dir=destino.parent, prefix=".tmp_", suffix=destino.suffix)
    os.close(fd)
    try:
        escribir(tmp)
        os.replace(tmp, destino)
    except BaseException:
        if os.path.exists(tmp):
            os.unlink(tmp)
        raise
