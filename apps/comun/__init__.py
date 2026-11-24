"""Utilidades comunes. Se limita OpenBLAS: reserva ~32 MB por hilo aunque no se use."""
import os

os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
