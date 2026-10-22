"""Acceso SQL a datos crudos y variables derivadas, sin modificar DuckDB."""
import duckdb
import holidays
import pandas as pd
from .configuracion import ROOT, INICIO, FIN, HORIZONTE

def conectar():
    return duckdb.connect(str(ROOT/'data/olist.duckdb'), read_only=True)

def consultar(con, archivo, parametros=None):
    # UTF-8 explícito: en Windows la codificación por defecto altera los acentos.
    return con.execute((ROOT/'sql'/archivo).read_text(encoding='utf-8'), parametros or []).df()

def preparar(con, fin=FIN):
    """También admite un fin temprano: permite auditar retirando todo el futuro."""
    serie = consultar(con, 'serie_diaria.sql', [INICIO, fin])
    # El calendario futuro es conocido; las ventas futuras no se inventan.
    fin_cal = pd.Timestamp(fin) + pd.Timedelta(days=HORIZONTE)
    feriados = holidays.country_holidays('BR', years=range(2017,fin_cal.year+1))
    festivos = pd.DataFrame({'fecha':pd.to_datetime(sorted(feriados.keys()))})
    con.register('festivos', festivos)
    calendario = consultar(con, 'calendario.sql', [INICIO,str(fin_cal.date())])
    con.register('serie',serie)
    con.register('calendario',calendario)
    variables = consultar(con, 'features.sql', [INICIO])
    return serie, calendario, variables

def exportar(tabla, nombre):
    (ROOT/'resultados').mkdir(exist_ok=True)
    tabla.to_csv(ROOT/'resultados'/f'{nombre}.csv', index=False)
