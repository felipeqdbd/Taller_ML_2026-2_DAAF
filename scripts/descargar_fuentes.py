"""Descarga una vez las fuentes tipográficas del informe y las guarda en recursos/fuentes/.

El informe PDF y las figuras usan Source Serif 4 (texto) y Source Sans 3 (títulos,
tablas y gráficas), publicadas por Adobe con licencia SIL Open Font License 1.1,
que permite redistribuirlas junto al proyecto. Se guardan versiones estáticas .ttf
porque ReportLab no admite fuentes variables. Si faltaran, el informe y las
figuras usan DejaVu, incluida en matplotlib.

Uso (desde la raíz del proyecto):  python scripts/descargar_fuentes.py
"""
from pathlib import Path
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
DESTINO = ROOT/'recursos'/'fuentes'
BASE = 'https://raw.githubusercontent.com/adobe-fonts'
FAMILIAS = {
    'source-serif': ['SourceSerif4-Regular', 'SourceSerif4-It', 'SourceSerif4-Semibold', 'SourceSerif4-Bold'],
    'source-sans': ['SourceSans3-Regular', 'SourceSans3-It', 'SourceSans3-Semibold', 'SourceSans3-Bold'],
}

def bajar(url, archivo):
    with urllib.request.urlopen(url, timeout=60) as respuesta:
        archivo.write_bytes(respuesta.read())
    print(f'{archivo.name}: {archivo.stat().st_size:,} bytes')

if __name__ == '__main__':
    DESTINO.mkdir(parents=True, exist_ok=True)
    for repo, nombres in FAMILIAS.items():
        for nombre in nombres:
            bajar(f'{BASE}/{repo}/release/TTF/{nombre}.ttf', DESTINO/f'{nombre}.ttf')
        bajar(f'{BASE}/{repo}/release/LICENSE.md', DESTINO/f'LICENCIA_{repo}.md')
