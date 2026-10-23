"""Descarga una vez la malla de estados (UF) de Brasil y la guarda en recursos/.

El notebook 00 dibuja los mapas con geopandas a partir de este archivo local, así
la ejecución no depende de internet. No son datos de Olist: es solo la cartografía
base sobre la que se pintan los resultados de las consultas SQL.

Fuentes, en orden: la API oficial de mallas del IBGE y, si no responde, la copia
pública de Code for America (derivada del IBGE). Las fronteras se simplifican
(~1 km) porque el mapa se dibuja a escala nacional.

Uso (desde la raíz del proyecto):  python scripts/descargar_mapa_brasil.py
"""
from pathlib import Path
import json
import urllib.request
import geopandas as gpd

ROOT = Path(__file__).resolve().parents[1]
DESTINO = ROOT/'recursos'/'brasil_uf.geojson'
FUENTES = [
    ('IBGE', 'https://servicodados.ibge.gov.br/api/v3/malhas/paises/BR'
             '?formato=application/vnd.geo+json&qualidade=minima&intrarregiao=UF'),
    ('Code for America', 'https://raw.githubusercontent.com/codeforamerica/click_that_hood/'
                         'master/public/data/brazil-states.geojson'),
]
# Código IBGE -> sigla de dos letras, que es como Olist identifica el estado.
SIGLAS = {'11': 'RO', '12': 'AC', '13': 'AM', '14': 'RR', '15': 'PA', '16': 'AP', '17': 'TO',
          '21': 'MA', '22': 'PI', '23': 'CE', '24': 'RN', '25': 'PB', '26': 'PE', '27': 'AL',
          '28': 'SE', '29': 'BA', '31': 'MG', '32': 'ES', '33': 'RJ', '35': 'SP', '41': 'PR',
          '42': 'SC', '43': 'RS', '50': 'MS', '51': 'MT', '52': 'GO', '53': 'DF'}

def descargar():
    for nombre, url in FUENTES:
        try:
            with urllib.request.urlopen(url, timeout=60) as respuesta:
                return nombre, json.load(respuesta)
        except OSError as error:
            print(f'{nombre} no respondió ({error}); se intenta la siguiente fuente.')
    raise RuntimeError('Ninguna fuente de la malla respondió.')

def main():
    fuente, malla = descargar()
    for rasgo in malla['features']:
        p = rasgo['properties']
        codigo = str(p.get('codarea') or p.get('codigo_ibg'))
        rasgo['properties'] = {'codigo_ibge': codigo, 'estado': SIGLAS[codigo]}
    estados = gpd.GeoDataFrame.from_features(malla['features'], crs='EPSG:4326')
    assert len(estados) == 27 and estados.estado.is_unique, 'Se esperaban 26 estados y el Distrito Federal'
    estados['geometry'] = estados.geometry.simplify(0.01, preserve_topology=True)
    DESTINO.parent.mkdir(exist_ok=True)
    estados.sort_values('estado').to_file(DESTINO, driver='GeoJSON')
    print(f'Malla de {fuente} guardada en {DESTINO.relative_to(ROOT)} ({DESTINO.stat().st_size/1024:.0f} KB).')

if __name__ == '__main__':
    main()
