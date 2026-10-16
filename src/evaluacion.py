"""Métricas e intervalos empíricos; no prometen cobertura futura exacta."""
import duckdb
import numpy as np
import pandas as pd
from .configuracion import NIVEL

def metricas(predicciones,grupos=('modelo',)):
    """Cada par origen-horizonte pesa igual; el solapamiento no se elimina."""
    d=predicciones.copy()
    d['absoluto']=abs(d.real-d.pred)
    d['cuadrado']=(d.real-d.pred)**2
    den=abs(d.real)+abs(d.pred)
    d['smape']=200*d.absoluto/den.where(den.ne(0),1)
    d['sesgo']=d.pred-d.real  # Positivo significa sobrepronóstico.
    g=d.groupby(list(grupos),dropna=False).agg(
        MAE=('absoluto','mean'),MSE=('cuadrado','mean'),sMAPE=('smape','mean'),
        sesgo=('sesgo','mean'),n=('real','size'))
    g['RMSE']=np.sqrt(g.pop('MSE'))
    return g.reset_index()[[*grupos,'MAE','RMSE','sMAPE','sesgo','n']]

def totales_semanales(predicciones):
    """Suma primero los puntos y reales; los intervalos se calibran DESPUÉS.

    Semana 1=h1..7, semana 2=h8..14, etc.: miércoles a martes en este protocolo.
    No se suman límites diarios. Para el futuro, real permanece desconocido.
    """
    with duckdb.connect() as con:
        con.register('p',predicciones)
        return con.sql('''SELECT modelo,origen,((h-1)//7+1)::INTEGER semana,
            min(fecha) desde,max(fecha) hasta,sum(real) AS real,sum(pred) AS pred
            FROM p GROUP BY 1,2,3 ORDER BY modelo,origen,semana''').df()

def calibrar(predicciones,metodo='relativo',semanal=False,nivel=NIVEL):
    """Orden estadístico exacto, sin interpolación de cuantiles.

    Diario: agrupa errores por semana del horizonte. Semanal: cada residuo
    corresponde al total de siete días de una emisión. Los errores temporales
    son dependientes y se reajusta el modelo: la corrección de rango NO aporta
    por sí sola una garantía conformal de intercambiabilidad.
    """
    if metodo not in ('absoluto','relativo') or not 0<nivel<1:
        raise ValueError('Método o nivel inválido.')
    d=totales_semanales(predicciones) if semanal else predicciones.copy()
    if not semanal:
        d['semana']=(d.h-1)//7+1
    filas=[]
    for semana,g in d.groupby('semana'):
        escala=1+g.pred.to_numpy() if metodo=='relativo' else np.ones(len(g))
        errores=np.sort(abs(g.real.to_numpy()-g.pred.to_numpy())/escala)
        assert np.isfinite(errores).all()
        n=len(errores); k=int(np.ceil((n+1)*nivel))
        if k>n:
            raise ValueError(f'{n} residuos no permiten un cuantil finito de nivel {nivel}.')
        filas.append(dict(semana=int(semana),n=n,rango=k,cuantil=float(errores[k-1]),
                          metodo=metodo,unidad='total_semanal' if semanal else 'diaria',nivel=nivel))
    return pd.DataFrame(filas)

def aplicar_intervalos(predicciones,calibracion,semanal=False):
    d=totales_semanales(predicciones) if semanal else predicciones.copy()
    if not semanal:
        d['semana']=(d.h-1)//7+1
    metodo=calibracion.metodo.iloc[0]
    q=d.semana.map(calibracion.set_index('semana').cuantil)
    ancho=q*(1+d.pred) if metodo=='relativo' else q
    d['inferior']=np.maximum(0,d.pred-ancho)
    d['superior']=d.pred+ancho
    d['metodo_intervalo']=metodo
    return d

def cobertura(intervalos,grupos=('metodo_intervalo',)):
    d=intervalos.copy()
    assert d.real.notna().all()
    d['cubierto']=d.real.between(d.inferior,d.superior)
    d['ancho']=d.superior-d.inferior
    return d.groupby(list(grupos)).agg(cubiertos=('cubierto','sum'),
        n=('cubierto','size'),cobertura=('cubierto','mean'),ancho_medio=('ancho','mean')).reset_index()
