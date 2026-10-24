"""Ejecuta los tres notebooks en orden, cada uno con un kernel limpio.

Guarda incluso una ejecución fallida para poder inspeccionar su celda; propaga
el error y nunca informa éxito si algún notebook falla.
"""
from pathlib import Path
import json
import os
import sys
import tempfile
import nbformat
from nbclient import NotebookClient

ROOT=Path(__file__).resolve().parents[1]
os.environ.setdefault('MPLCONFIGDIR','/tmp/olist_pronostico_matplotlib')
os.environ.setdefault('IPYTHONDIR','/tmp/olist_pronostico_ipython')
os.environ.setdefault('JUPYTER_RUNTIME_DIR','/tmp/olist_pronostico_jupyter')
os.environ.setdefault('JUPYTER_PLATFORM_DIRS','1')
with tempfile.TemporaryDirectory(prefix='olist_kernel_') as kernel_root:
    # Un kernel local evita que "python3" resuelva al Python global del equipo.
    spec_dir = Path(kernel_root)/'kernels'/'python3'
    spec_dir.mkdir(parents=True)
    (spec_dir/'kernel.json').write_text(json.dumps({
        'argv': [sys.executable, '-m', 'ipykernel_launcher', '-f', '{connection_file}'],
        'display_name': 'Python 3 (entorno actual)',
        'language': 'python',
    }), encoding='utf-8')
    os.environ['JUPYTER_PATH'] = kernel_root + os.pathsep + os.environ.get('JUPYTER_PATH', '')
    for path in sorted((ROOT/'notebooks').glob('*.ipynb')):
        print('Ejecutando',path.name,flush=True)
        nb=nbformat.read(path,as_version=4)
        try:
            NotebookClient(nb,timeout=1800,resources={'metadata':{'path':str(ROOT)}},
                           kernel_name='python3').execute()
        finally:
            nbformat.write(nb,path)
        print('Completado',path.name,flush=True)
