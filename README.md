# Ingeniería inversa de cuatro programas y réplicas con IA local

Práctica de Inteligencia Artificial, UNAMAD. Estudiante: Jorge Antonio Diaz Ancco (22221038).
Docente: Miguel Ángel Alatrista Aguilar.

| Op. | Original | Réplica | IA local |
|---|---|---|---|
| A | OpenOffice Writer (Apache 2.0) | `apps/escritor` | Corregir, resumir, autocompletar (Llama 3) |
| B | Microsoft Paint (comercial) | `apps/lienzo` | Quitar fondo (U²-Net), reconocer bocetos (CLIP) |
| C | SumatraPDF (GPL-3.0) | `apps/lector` | Chat con el PDF (RAG: bge-m3 + Llama 3.1) |
| D | IrfanView (propietario, gratuito) | `apps/conversor` | Clasificar fauna y flora amazónica (CLIP) |

## Instalar (Windows, Python 3.10+)

```
python -m venv .venv
.venv\Scripts\pip install -r requirements.txt
.venv\Scripts\python descargar_modelos.py
ollama pull llama3.1:8b
ollama pull llama3.2:3b
ollama pull bge-m3
```

## Ejecutar

```
.venv\Scripts\python apps\escritor\main.py
.venv\Scripts\python apps\lienzo\main.py
.venv\Scripts\python apps\lector\main.py archivo.pdf
.venv\Scripts\python apps\conversor\main.py
.venv\Scripts\python -m pytest tests
```

## Contenido

- `analisis/`: inspección (UI Automation, menús, archivos mínimos, Process Monitor).
- `evidencias/`: árboles de interfaz, capturas, accesos a disco y resultados medidos.
- `prompts/`: prompts estructurados (3 por programa). `tests/`: pruebas y evaluación de la IA.
- `informe/` y `presentacion/`: entregables.

El código se generó con asistencia de Claude (Claude Code) bajo dirección del estudiante; el proceso y los errores
depurados están en el informe. No se descompiló ningún programa. Fines académicos. Los créditos de las fotos están en
`evaluacion/creditos_fotos*.csv`; los bocetos provienen de Quick, Draw! (CC BY 4.0).
