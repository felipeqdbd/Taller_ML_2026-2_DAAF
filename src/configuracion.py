"""Protocolo explícito: no se modifica a partir de los resultados de prueba.

El conjunto es histórico y ya conocido: las métricas son retrospectivas.
Los intervalos de fechas evaluadas de selección, calibración y prueba no se
cruzan. Dentro de cada etapa sí se solapan las ventanas de 28 días.
"""
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
INICIO = '2017-02-01'
FIN = '2018-08-21'
HORIZONTE = 28
NIVEL = 0.90
SELECCION = pd.date_range('2017-07-25', '2018-02-13', freq='7D')
CALIBRACION = pd.date_range('2018-03-13', '2018-05-29', freq='7D')
PRUEBA = pd.date_range('2018-06-26', '2018-07-24', freq='7D')

def particiones():
    """Una fila por emisión; una fecha real puede aparecer en varias emisiones."""
    return pd.DataFrame([
        dict(etapa=etapa, origen=o, desde=o + pd.Timedelta(days=1),
             hasta=o + pd.Timedelta(days=HORIZONTE))
        for etapa, origenes in [('seleccion', SELECCION),
                               ('calibracion', CALIBRACION), ('prueba', PRUEBA)]
        for o in origenes
    ])
