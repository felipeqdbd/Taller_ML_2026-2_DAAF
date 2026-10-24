"""Modelos comparables: una emisión al cierre del origen, 28 predicciones.

Todos usan únicamente etiquetas conocidas. ETS y SARIMAX pronostican de forma
recursiva (propagan su estado h pasos). El ML es directo global: aprende una
función de historia, calendario y horizonte; no introduce ventas reales de los
días intermedios ni alimenta recursivamente sus propias predicciones.
"""
import warnings
import duckdb
import numpy as np
import pandas as pd
from lightgbm import LGBMRegressor
from statsmodels.tsa.holtwinters import ExponentialSmoothing
from statsmodels.tsa.statespace.sarimax import SARIMAX
from statsmodels.stats.diagnostic import acorr_ljungbox
from .configuracion import HORIZONTE, NIVEL

CALENDARIO = ['h','dia_semana','dia_mes','mes','tendencia','festivo','carnaval',
              'black_friday','post_black_friday','fin_anio']
BASICAS = ['lag_0','lag_6','lag_13','lag_27','media_7','media_28','sd_28'] + CALENDARIO
AMPLIAS = BASICAS + [f'lag_{i}' for i in range(1,6)] + [
    'media_91','razon_7_28','razon_28_91','cv_28',
    'ultimo_mismo_dia','media_4_mismo_dia',
    *[f'rel_lag_{i}' for i in range(7)], 'rel_mismo_dia','rel_media_4_dias']
CONFIG_ML = dict(objective='regression_l1', learning_rate=0.03,
    num_leaves=7,n_estimators=300,min_child_samples=40,reg_lambda=1.0,
    random_state=2026,n_jobs=1,deterministic=True,force_col_wise=True,verbosity=-1)
# Eventos de calendario que se modelan (decisión de B_series_01_exploracion, §3.3).
EVENTOS = ['festivo','carnaval','black_friday','post_black_friday','fin_anio']
MODELOS = ['Ingenuo','Estacional_7','ETS_amortiguado','SARIMAX_solo_semana','SARIMAX_calendario',
           'LGBM_base_absoluto','LGBM_amplio_absoluto',
           'LGBM_base_relativo','LGBM_amplio_relativo']

def matrices(variables, origen):
    """La fecha de ETIQUETA, además de la de origen, debe estar en el pasado."""
    with duckdb.connect() as con:
        con.register('variables',variables)
        entrenamiento=con.execute('''SELECT * FROM variables
            WHERE fecha<=CAST(? AS DATE) AND real IS NOT NULL ORDER BY origen,h''',
            [str(pd.Timestamp(origen).date())]).df()
        futuro=con.execute('SELECT * FROM variables WHERE origen=CAST(? AS DATE) ORDER BY h',
                           [str(pd.Timestamp(origen).date())]).df()
    assert len(futuro)==HORIZONTE
    assert entrenamiento.fecha.max()<=origen
    assert futuro.fecha.min()>origen
    return entrenamiento,futuro

def exogenas(calendario):
    """Regresores conocidos por calendario; domingo es la referencia semanal.

    No se usa un indicador de huelga futura: su ocurrencia no se conocía con
    cuatro semanas de antelación. Sus días permanecen en todas las métricas.
    """
    x=calendario.set_index('fecha')[EVENTOS].copy()
    for dia in range(1,7):
        x[f'dia_{dia}']=(x.index.dayofweek==dia-1).astype(int)
    return x.astype(float).asfreq('D')

def _sarimax(historia, x, origen, info, detalles):
    """ARIMA(1,1,1) sobre log1p con regresores conocidos; devuelve puntos e intervalo.

    El intervalo paramétrico supone errores normales en log y un modelo bien
    especificado; se transforma con expm1, que es monótona.
    """
    pasado=x.loc[historia.index]
    # Un evento aún no observado no permite estimar su coeficiente.
    columnas=pasado.columns[pasado.nunique()>1]
    pasado=pasado[columnas]
    modelo=SARIMAX(np.log1p(historia),exog=pasado,
        order=(1,1,1),seasonal_order=(0,0,0,0),trend='n',
        enforce_stationarity=True,enforce_invertibility=True)
    fit=modelo.fit(disp=False,maxiter=300)
    # Secuencia de optimizadores fijada por anticipado, no por MAE.
    info['optimizador']='lbfgs'
    if not fit.mle_retvals.get('converged',False):
        fit=modelo.fit(start_params=fit.params,method='bfgs',disp=False,maxiter=500)
        info['optimizador']='bfgs'
    info['convergencia']=bool(fit.mle_retvals.get('converged',False))
    info['AIC']=float(fit.aic)
    info['regresores']=', '.join(columnas)
    fechas=pd.date_range(origen+pd.Timedelta(days=1),periods=HORIZONTE)
    # Pronóstico recursivo: el filtro propaga el estado h pasos con el calendario futuro.
    fc=fit.get_forecast(HORIZONTE,exog=x.loc[fechas,columnas])
    limites=np.expm1(np.asarray(fc.conf_int(alpha=1-NIVEL)))
    info['inferior_param']=np.maximum(limites[:,0],0).tolist()
    info['superior_param']=limites[:,1].tolist()
    # Diagnóstico descriptivo de innovaciones después de inicialización.
    resid=fit.filter_results.standardized_forecasts_error[0]
    resid=resid[max(28,fit.loglikelihood_burn):]
    lb=acorr_ljungbox(resid,lags=[7,14],model_df=2,return_df=True)
    info['Ljung_Box_p7']=float(lb.lb_pvalue.iloc[0])
    info['Ljung_Box_p14']=float(lb.lb_pvalue.iloc[1])
    if detalles:
        info['residuos']=resid.tolist()
        info['coeficientes']=fit.params.to_dict()
    return np.expm1(np.asarray(fc.predicted_mean))

def predecir(nombre, y, variables, calendario, origen, detalles=False):
    """Devuelve predicciones y metadatos de ajuste; recorta negativos a cero.

    En L1 se aproxima una mediana condicional. Al invertir log1p tampoco se
    obtiene automáticamente la media en la escala original.
    """
    origen=pd.Timestamp(origen)
    historia=y.loc[:origen].astype(float)
    info={'modelo':nombre,'origen':str(origen.date()),'n_dias':len(historia),
          'convergencia':True,'avisos':''}
    with warnings.catch_warnings(record=True) as avisos:
        warnings.simplefilter('always')
        if nombre=='Ingenuo':
            pred=np.repeat(historia.iloc[-1],HORIZONTE)
        elif nombre=='Estacional_7':
            pred=np.tile(historia.iloc[-7:].to_numpy(),HORIZONTE//7)
        elif nombre=='ETS_amortiguado':
            # En log1p la semana aditiva equivale a una semana multiplicativa en pedidos.
            fit=ExponentialSmoothing(np.log1p(historia),trend='add',damped_trend=True,
                seasonal='add',seasonal_periods=7,initialization_method='estimated').fit()
            info['convergencia']=bool(fit.mle_retvals.get('success',True))
            info['AIC']=float(fit.aic)
            pred=np.expm1(fit.forecast(HORIZONTE).to_numpy())
        elif nombre=='SARIMAX_solo_semana':
            # Misma estructura sin eventos: mide cuánto aporta modelarlos.
            x=exogenas(calendario).drop(columns=EVENTOS)
            pred=_sarimax(historia,x,origen,info,detalles)
        elif nombre=='SARIMAX_calendario':
            pred=_sarimax(historia,exogenas(calendario),origen,info,detalles)
        elif nombre.startswith('LGBM_'):
            train,future=matrices(variables,origen)
            columnas=AMPLIAS if '_amplio_' in nombre else BASICAS
            relativo=nombre.endswith('_relativo')
            objetivo=train.real.to_numpy(dtype=float)
            if relativo:
                # r=log((1+y)/(1+media28)). La inversión usa media28 DEL ORIGEN.
                objetivo=np.log1p(objetivo)-np.log1p(train.media_28.to_numpy())
            fit=LGBMRegressor(**CONFIG_ML)
            fit.fit(train[columnas],objetivo)
            pred=fit.predict(future[columnas])
            if relativo:
                pred=np.expm1(pred+np.log1p(future.media_28.to_numpy()))
            info['filas_entrenamiento']=len(train)
            info['ultima_etiqueta']=str(train.fecha.max().date())
            if detalles:
                info['importancia_gain']=dict(zip(columnas,fit.booster_.feature_importance('gain').tolist()))
        else:
            raise ValueError(f'Modelo desconocido: {nombre}')
    info['avisos']=' | '.join(sorted({f'{type(a.message).__name__}: {a.message}' for a in avisos}))
    if not info['convergencia']:
        raise RuntimeError(f'Ajuste sin convergencia: {nombre}, {origen.date()}; revisar antes de evaluar.')
    pred=np.maximum(np.asarray(pred,dtype=float),0)
    assert pred.shape==(HORIZONTE,) and np.isfinite(pred).all()
    return pred,info

def evaluar(y,variables,calendario,origenes,nombres):
    """Expansión histórica y reajuste completo en cada emisión semanal."""
    filas=[]; ajustes=[]
    for origen in origenes:
        fechas=pd.date_range(origen+pd.Timedelta(days=1),periods=HORIZONTE)
        real=y.reindex(fechas).to_numpy()
        assert np.isfinite(real).all()
        for nombre in nombres:
            pred,info=predecir(nombre,y,variables,calendario,origen)
            # Solo SARIMAX trae intervalo paramétrico; los demás quedan en NaN.
            vacio=[np.nan]*HORIZONTE
            filas.append(pd.DataFrame(dict(modelo=nombre,origen=origen,fecha=fechas,
                h=np.arange(1,HORIZONTE+1),real=real,pred=pred,
                inferior_param=info.pop('inferior_param',vacio),
                superior_param=info.pop('superior_param',vacio))))
            ajustes.append(info)
        print(f'{origen.date()}: {len(nombres)} modelos, {HORIZONTE} horizontes.',flush=True)
    return pd.concat(filas,ignore_index=True),pd.DataFrame(ajustes)
