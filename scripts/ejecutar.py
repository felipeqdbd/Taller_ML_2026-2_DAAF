"""Ejecuta los tres notebooks en orden, cada uno con un kernel limpio.

Guarda incluso una ejecución fallida para poder inspeccionar su celda; propaga
el error y nunca informa éxito si algún notebook falla.
"""
from pathlib import Path
import os
import nbformat
from nbclient import NotebookClient

ROOT=Path(__file__).resolve().parents[1]
os.environ.setdefault('MPLCONFIGDIR','/tmp/olist_pronostico_matplotlib')
os.environ.setdefault('IPYTHONDIR','/tmp/olist_pronostico_ipython')
os.environ.setdefault('JUPYTER_RUNTIME_DIR','/tmp/olist_pronostico_jupyter')
os.environ.setdefault('JUPYTER_PLATFORM_DIRS','1')
for path in sorted((ROOT/'notebooks').glob('*.ipynb')):
    print('Ejecutando',path.name,flush=True)
    nb=nbformat.read(path,as_version=4)
    try:
        NotebookClient(nb,timeout=1800,resources={'metadata':{'path':str(ROOT)}},
                       kernel_name='python3').execute()
    finally:
        nbformat.write(nb,path)
    print('Completado',path.name,flush=True)
