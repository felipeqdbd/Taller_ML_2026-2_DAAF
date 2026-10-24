"""Protocolo explícito: no se modifica a partir de los resultados de prueba.

El conjunto es histórico y ya conocido: las métricas son retrospectivas.
Los intervalos de fechas evaluadas de selección, calibración y prueba no se
cruzan. Dentro de cada etapa sí se solapan las ventanas de 28 días.
"""
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
INICIO = '2017-02-01'
# Último día con cobertura continua (Módulo 0). La serie se corta en el último
# domingo <= CORTE (serie_diaria.sql); FIN repite esa regla para el resto del código.
CORTE = '2018-08-21'
FIN = str((pd.Timestamp(CORTE) - pd.Timedelta(days=(pd.Timestamp(CORTE).dayofweek + 1) % 7)).date())
HORIZONTE = 28
NIVEL = 0.90
# Orígenes en domingo: cada emisión pronostica 4 semanas lunes-domingo.
SELECCION = pd.date_range('2017-07-23', '2018-02-11', freq='7D')
CALIBRACION = pd.date_range('2018-03-11', '2018-05-27', freq='7D')
PRUEBA = pd.date_range('2018-06-24', '2018-07-22', freq='7D')
assert all(o.dayofweek == 6 for o in SELECCION.append([CALIBRACION, PRUEBA]))
assert PRUEBA[-1] + pd.Timedelta(days=HORIZONTE) == pd.Timestamp(FIN)
# Episodios que calendario.sql no incluye. Sirven para describir días y medir
# errores; no son regresores. previsible = la fecha se conocía de antemano.
# pre_navidad solo se observó en diciembre de 2017 (objetivo de selección), por eso
# no se convierte en indicador. Solo se listan fechas anteriores a la prueba: los
# partidos posteriores de Brasil en el Mundial caen en prueba y no se examinan.
EPISODIOS = pd.DataFrame([
    ('pre_navidad', '2017-12-14', '2017-12-23', True),
    ('huelga_camioneros', '2018-05-21', '2018-05-31', False),
    ('mundial_brasil', '2018-06-17', '2018-06-17', True),
    ('mundial_brasil', '2018-06-22', '2018-06-22', True),
], columns=['evento', 'desde', 'hasta', 'previsible'])

def particiones():
    """Una fila por emisión; una fecha real puede aparecer en varias emisiones."""
    return pd.DataFrame([
        dict(etapa=etapa, origen=o, desde=o + pd.Timedelta(days=1),
             hasta=o + pd.Timedelta(days=HORIZONTE))
        for etapa, origenes in [('seleccion', SELECCION),
                               ('calibracion', CALIBRACION), ('prueba', PRUEBA)]
        for o in origenes
    ])
