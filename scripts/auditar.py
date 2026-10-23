"""Comprueba la entrega mediante cálculos independientes y pruebas temporales.

No basta con que un notebook termine: conciliamos SQL crudo, métricas,
definiciones de baselines, cuantiles y reproducibilidad sin ventas futuras.
"""
from pathlib import Path
import sys,json,hashlib,importlib.metadata,platform
import duckdb
import numpy as np
import pandas as pd
import nbformat

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from src.configuracion import INICIO,FIN,SELECCION,CALIBRACION,PRUEBA,NIVEL
from src.datos import conectar,preparar
from src.modelos import MODELOS,AMPLIAS,predecir,matrices

R=ROOT/'resultados'
checks=[]
def ok(nombre,detalle):
    checks.append(dict(comprobacion=nombre,estado='OK',detalle=detalle))
    print('OK:',nombre,flush=True)
def leer(nombre,fechas=()):
    return pd.read_csv(R/f'{nombre}.csv',parse_dates=list(fechas))

con=conectar()
serie,calendario,f=preparar(con)
y=serie.set_index('fecha').y.asfreq('D')
r=json.loads((R/'resumen.json').read_text(encoding='utf-8'))
guardada=leer('serie_diaria',['fecha'])
pd.testing.assert_frame_equal(serie,guardada,check_dtype=False)
raw=con.execute('''SELECT count(*),count(DISTINCT order_id) FROM orders
 WHERE order_purchase_timestamp>=CAST(? AS DATE)
 AND order_purchase_timestamp<CAST(? AS DATE)+INTERVAL 1 DAY''',[INICIO,FIN]).fetchall()[0]  # fetchall cierra el resultado
assert len(serie)==565 and serie.y.sum()==raw[0]==raw[1]==97091
assert serie.fecha.max()==pd.Timestamp(FIN) and pd.Timestamp(FIN).dayofweek==6
assert serie.fecha.is_unique and serie.fecha.diff().dropna().eq(pd.Timedelta(days=1)).all()
ok('Serie conciliada con compras',f'{len(serie)} días consecutivos, {raw[0]} órdenes distintas; exportación idéntica a SQL.')

partes=leer('particiones',['origen','desde','hasta'])
for etapa,orig in [('seleccion',SELECCION),('calibracion',CALIBRACION),('prueba',PRUEBA)]:
    p=partes[partes.etapa.eq(etapa)]
    assert p.origen.to_list()==list(orig)
    assert p.desde.eq(p.origen+pd.Timedelta(days=1)).all()
    assert p.hasta.eq(p.origen+pd.Timedelta(days=28)).all()
assert partes[partes.etapa.eq('seleccion')].hasta.max()<partes[partes.etapa.eq('calibracion')].desde.min()
assert partes[partes.etapa.eq('calibracion')].hasta.max()<partes[partes.etapa.eq('prueba')].desde.min()
assert partes[partes.etapa.eq('prueba')].desde.min()==y.index[-56]
ok('Protocolo temporal','30/12/5 emisiones; los objetivos de las tres etapas no se cruzan; prueba ocupa los últimos 56 días.')

preds={}
for etapa,origenes in [('seleccion',SELECCION),('calibracion',CALIBRACION),('prueba',PRUEBA)]:
    pred=leer(f'predicciones_{etapa}',['origen','fecha']); preds[etapa]=pred
    nombres=[r['ganador']] if etapa=='calibracion' else MODELOS
    assert set(pred.modelo)==set(nombres)
    assert len(pred)==len(origenes)*len(nombres)*28
    assert not pred.duplicated(['modelo','origen','h']).any()
    assert (pred.fecha-pred.origen).dt.days.eq(pred.h).all()
    assert pred.pred.ge(0).all() and np.isfinite(pred.pred).all()
    assert set(pred.origen)==set(origenes)
    assert pred.groupby(['modelo','origen']).h.apply(lambda h:set(h)==set(range(1,29))).all()
    np.testing.assert_array_equal(pred.real,y.reindex(pred.fecha).to_numpy())
    if etapa!='calibracion':
        con.register('p_auditada',pred)
        for sufijo,grupos in [('', ['modelo']),('_horizonte',['modelo','h']),('_origen',['modelo','origen'])]:
            cols=','.join(grupos)
            calc=con.sql(f'''SELECT {cols},avg(abs(real-pred)) MAE,
                sqrt(avg(pow(real-pred,2))) RMSE,avg(100*abs(real-pred)/real) MAPE,
                avg(CASE WHEN abs(real)+abs(pred)=0 THEN 0 ELSE 200*abs(real-pred)/(abs(real)+abs(pred)) END) sMAPE,
                avg(pred-real) sesgo,count(*) n FROM p_auditada GROUP BY {cols} ORDER BY {cols}''').df()
            saved=leer(f'metricas{sufijo}_{etapa}', ['origen'] if 'origen' in grupos else [])
            saved=saved.sort_values(grupos).reset_index(drop=True)
            pd.testing.assert_frame_equal(calc[grupos],saved[grupos],check_dtype=False)
            np.testing.assert_allclose(calc[['MAE','RMSE','MAPE','sMAPE','sesgo','n']],saved[['MAE','RMSE','MAPE','sMAPE','sesgo','n']],atol=1e-9)
        # Solo SARIMAX trae intervalo paramétrico y debe contener a su pronóstico.
        sx=pred.modelo.str.startswith('SARIMAX')
        assert pred.loc[~sx,['inferior_param','superior_param']].isna().all().all()
        assert pred[sx].inferior_param.le(pred[sx].pred+1e-9).all() and pred[sx].pred.le(pred[sx].superior_param+1e-9).all()
        for fila in pred[pred.modelo.isin(['Ingenuo','Estacional_7'])].itertuples():
            fuente=fila.origen if fila.modelo=='Ingenuo' else fila.origen-pd.Timedelta(days=6-(fila.h-1)%7)
            assert fila.pred==y.loc[fuente]
    ajustes=leer(f'ajustes_{etapa}')
    assert ajustes.convergencia.eq(True).all()
    ml=ajustes[ajustes.modelo.str.startswith('LGBM')]
    if len(ml):
        assert pd.to_datetime(ml.ultima_etiqueta).le(pd.to_datetime(ml.origen)).all()
    ok(f'Predicciones y ajustes de {etapa}',f'{len(pred)} pares; reales, horizontes, convergencia, métricas SQL y referencias conciliados según corresponda.')

# El ganador debe salir de selección, aunque la clasificación de prueba difiera.
ms=leer('metricas_seleccion').sort_values(['MAE','modelo'])
assert r['ganador']==ms.iloc[0].modelo
ok('Elección reproducible','El modelo final corresponde al mínimo MAE de selección; no se elige por prueba.')

# Verificación numérica de TODOS los orígenes de características.
for origen,g in f.groupby('origen'):
    historial=y.loc[:origen]
    np.testing.assert_allclose(g.media_7,historial.iloc[-7:].mean())
    np.testing.assert_allclose(g.media_28,historial.iloc[-28:].mean())
    np.testing.assert_allclose(g.media_91,historial.iloc[-91:].mean())
    np.testing.assert_allclose(g.sd_28,historial.iloc[-28:].std(ddof=1))
    for lag in [0,1,2,3,4,5,6,13,27]:
        np.testing.assert_allclose(g[f'lag_{lag}'],y.loc[origen-pd.Timedelta(days=lag)])
    for fila in g.itertuples():
        # Búsqueda independiente por weekday, sin usar la fórmula SQL del desplazamiento.
        mismos=historial[historial.index.dayofweek==fila.fecha.dayofweek].iloc[-4:]
        np.testing.assert_allclose(fila.ultimo_mismo_dia,mismos.iloc[-1])
        np.testing.assert_allclose(fila.media_4_mismo_dia,mismos.mean())
    np.testing.assert_allclose(g.razon_7_28,g.media_7/(1+g.media_28))
    np.testing.assert_allclose(g.razon_28_91,g.media_28/(1+g.media_91))
    np.testing.assert_allclose(g.cv_28,g.sd_28/(1+g.media_28))
    for lag in range(7):
        np.testing.assert_allclose(g[f'rel_lag_{lag}'],np.log1p(g[f'lag_{lag}'])-np.log1p(g.media_28),atol=1e-12)
    np.testing.assert_allclose(g.rel_mismo_dia,np.log1p(g.ultimo_mismo_dia)-np.log1p(g.media_28),atol=1e-12)
    np.testing.assert_allclose(g.rel_media_4_dias,np.log1p(g.media_4_mismo_dia)-np.log1p(g.media_28),atol=1e-12)
ok('Ventanas y variables históricas',f'{f.origen.nunique()} orígenes y {len(f)} pares: medias, dispersión, rezagos, día comparable y razones conciliados.')

# Contrastar festivos y fórmula de Black Friday mediante otra construcción.
for year in [2017,2018]:
    jueves=pd.date_range(f'{year}-11-01',f'{year}-11-30',freq='W-THU')[3]
    bf=jueves+pd.Timedelta(days=1)
    g=calendario[calendario.fecha.dt.year.eq(year)]
    esperado=g.fecha.eq(bf).astype(int)
    np.testing.assert_array_equal(g.black_friday,esperado)
# Carnaval: lunes y martes, 48 y 47 días antes de la Pascua (construcción independiente).
from dateutil.easter import easter
for year in [2017,2018]:
    pascua=pd.Timestamp(easter(year))
    g=calendario[calendario.fecha.dt.year.eq(year)]
    esperado=g.fecha.isin([pascua-pd.Timedelta(days=48),pascua-pd.Timedelta(days=47)]).astype(int)
    np.testing.assert_array_equal(g.carnaval,esperado)
ok('Calendario de Black Friday y Carnaval','Black Friday coincide con el día posterior al cuarto jueves de noviembre; Carnaval con Pascua − 48 y − 47 días.')

# Los ejemplos visibles en el notebook deben reflejar exactamente el calendario
# usado por los modelos y mostrar un festivo futuro sin ventas observadas.
ejemplos=leer('ejemplos_calendario',['fecha'])
columnas=['dia_semana','festivo','black_friday','post_black_friday','fin_anio']
referencia=ejemplos[['fecha']].merge(calendario[['fecha',*columnas]],on='fecha',validate='one_to_one')
pd.testing.assert_frame_equal(ejemplos[['fecha',*columnas]],referencia,check_dtype=False)
festivo_futuro=ejemplos.set_index('fecha').loc[pd.Timestamp('2018-09-07')]
assert festivo_futuro.festivo==1 and pd.isna(festivo_futuro.pedidos_observados)
assert ejemplos.set_index('fecha').loc[pd.Timestamp('2017-11-24'),'black_friday']==1
evento=leer('ejemplo_variables_evento',['origen','fecha'])
assert evento.loc[evento.fecha.eq(pd.Timestamp('2017-11-24')),'black_friday'].iloc[0]==1
assert evento.fecha.sub(evento.origen).dt.days.eq(evento.h).all()
ok('Calendario visible en notebooks','Festivo futuro sin ventas observadas y Black Friday con indicador coherente en el calendario y en variables de entrenamiento.')

# Retirar el futuro requiere reconstruir SQL desde orders hasta el corte.
for corte,etapa in [(SELECCION[0],'seleccion'),(PRUEBA[0],'prueba')]:
    st,ct,ft=preparar(con,str(corte.date()))
    tr,fu=matrices(f,corte); tr_t,fu_t=matrices(ft,corte)
    pd.testing.assert_frame_equal(tr[['origen','fecha','h','real',*AMPLIAS]],
                                  tr_t[['origen','fecha','h','real',*AMPLIAS]],check_dtype=False)
    np.testing.assert_allclose(fu[AMPLIAS],fu_t[AMPLIAS],atol=1e-12)
    for nombre in MODELOS:
        pt,_=predecir(nombre,st.set_index('fecha').y.asfreq('D'),ft,ct,corte)
        saved=preds[etapa].loc[lambda d:d.modelo.eq(nombre)&d.origen.eq(corte)].sort_values('h')
        np.testing.assert_allclose(pt,saved.pred,rtol=1e-7,atol=1e-6)
ok('Futuro físicamente retirado',f'Los {len(MODELOS)} modelos reproducen sus 28 pronósticos en el primer origen de selección y el primero de prueba.')

# Auditoría de cuantiles y totales, sin invocar calibrar ni aplicar_intervalos.
cal=preds['calibracion'].copy();cal['semana']=(cal.h-1)//7+1
weekly=cal.groupby(['modelo','origen','semana'],as_index=False)[['real','pred']].sum()
q=leer('cuantiles_intervalos')
assert len(q)==16
for fila in q.itertuples():
    base=weekly if fila.unidad=='total_semanal' else cal
    g=base[base.semana.eq(fila.semana)]
    errores=abs(g.real-g.pred)
    if fila.metodo=='relativo':errores=errores/(1+g.pred)
    ordenados=sorted(errores.to_list());k=int(np.ceil((len(g)+1)*NIVEL))
    assert fila.n==len(g) and fila.rango==k and k<=len(g)
    np.testing.assert_allclose(fila.cuantil,ordenados[k-1],atol=1e-10)
for unidad,archivo,covarchivo in [('diaria','intervalos_diarios_prueba','cobertura_diaria'),
                                  ('total_semanal','intervalos_semanales_prueba','cobertura_semanal')]:
    d=leer(archivo,['origen'])
    for metodo,g in d.groupby('metodo_intervalo'):
        qs=q[q.unidad.eq(unidad)&q.metodo.eq(metodo)].set_index('semana').cuantil
        ancho=g.semana.map(qs)*(1+g.pred) if metodo=='relativo' else g.semana.map(qs)
        np.testing.assert_allclose(g.inferior,np.maximum(0,g.pred-ancho),atol=1e-9)
        np.testing.assert_allclose(g.superior,g.pred+ancho,atol=1e-9)
        if unidad=='total_semanal':
            base=preds['prueba'][preds['prueba'].modelo.eq(r['ganador'])].copy()
            base['semana']=(base.h-1)//7+1
            agg=base.groupby(['origen','semana'],as_index=False)[['real','pred']].sum()
            comp=g.merge(agg,on=['origen','semana'],suffixes=('','_suma'),validate='one_to_one')
            np.testing.assert_allclose(comp[['real','pred']],comp[['real_suma','pred_suma']],atol=1e-9)
        cubiertos=g.real.between(g.inferior,g.superior)
        cov=leer(covarchivo).set_index('metodo_intervalo').loc[metodo]
        assert cov.cubiertos==cubiertos.sum() and cov.n==len(g)
        np.testing.assert_allclose(cov.cobertura,cubiertos.mean())
# Conformal del mejor ML: calibrado con sus propias predicciones de calibración.
cal_ml=leer('predicciones_calibracion_ml',['origen','fecha']);cal_ml['semana']=(cal_ml.h-1)//7+1
assert set(cal_ml.modelo)=={r['mejor_ml']} and len(cal_ml)==len(CALIBRACION)*28
np.testing.assert_array_equal(cal_ml.real,y.reindex(cal_ml.fecha).to_numpy())
q_ml=leer('cuantiles_intervalos_ml')
for fila in q_ml.itertuples():
    g=cal_ml[cal_ml.semana.eq(fila.semana)]
    ordenados=sorted((abs(g.real-g.pred)/(1+g.pred)).to_list());k=int(np.ceil((len(g)+1)*NIVEL))
    np.testing.assert_allclose(fila.cuantil,ordenados[k-1],atol=1e-10)
# Cobertura comparada: el paramétrico se recalcula desde las predicciones guardadas.
metodos=leer('cobertura_metodos').set_index('metodo_intervalo')
sx=preds['prueba'][preds['prueba'].modelo.eq('SARIMAX_calendario')]
dentro=sx.real.between(sx.inferior_param,sx.superior_param)
np.testing.assert_allclose(metodos.loc['parametrico_sarimax','cobertura'],dentro.mean())
np.testing.assert_allclose(metodos.loc['relativo','cobertura'],leer('cobertura_diaria').set_index('metodo_intervalo').loc['relativo','cobertura'])
ok('Intervalos diarios y totales','16 cuantiles por orden estadístico exacto; límites, sumas y coberturas conciliados sin reutilizar las funciones evaluadas. Conformal ML y paramétrico SARIMAX recalculados.')

final=leer('pronostico_diario_28_dias',['fecha','origen'])
assert len(final)==28 and final.fecha.min()==pd.Timestamp(FIN)+pd.Timedelta(days=1)
assert final.fecha.max()==pd.Timestamp(FIN)+pd.Timedelta(days=28)
pf,_=predecir(r['ganador'],y,f,calendario,FIN)
np.testing.assert_allclose(pf,final.pred,rtol=1e-7,atol=1e-6)
np.testing.assert_allclose(final.pred.sum(),r['total_puntos_28_dias'])
fs=leer('pronostico_semanal')
np.testing.assert_allclose(fs.pred.to_numpy(),final.pred.to_numpy().reshape(4,7).sum(axis=1))
assert final.real.isna().all() and fs.real.isna().all()
ok('Pronóstico histórico final','Reajuste reproducible, 28 fechas consecutivas, totales semanales coherentes y reales futuros desconocidos.')

notebooks=[]
for path in sorted((ROOT/'notebooks').glob('*.ipynb')):
    nb=nbformat.read(path,as_version=4);nbformat.validate(nb)
    codigo=[c for c in nb.cells if c.cell_type=='code']
    assert [c.execution_count for c in codigo]==list(range(1,len(codigo)+1))
    assert not any(o.output_type=='error' for c in codigo for o in c.outputs)
    imagenes=sum('image/png' in o.get('data',{}) for c in codigo for o in c.outputs)
    assert imagenes>0
    assert all('#' in c.source for c in codigo),path.name
    notebooks.append(dict(nombre=path.name,celdas_codigo=len(codigo),figuras=imagenes))
ok('Notebooks ejecutados y comentados','Tres notebooks con ejecución secuencial, sin errores, comentarios y figuras incrustadas para GitHub.')

con.close()
estado=dict(estado='OK',comprobaciones=checks,notebooks=notebooks,
    limite='Comprobaciones específicas y reproducibles; no prueban ausencia universal de errores ni validez futura.')
(R/'auditoria.json').write_text(json.dumps(estado,ensure_ascii=False,indent=2),encoding='utf-8')
paquetes=['duckdb','pandas','numpy','matplotlib','statsmodels','lightgbm','scikit-learn',
          'holidays','python-dateutil','geopandas','nbformat','nbclient','ipykernel','reportlab','kagglehub']
entorno=dict(python=platform.python_version(),paquetes={p:importlib.metadata.version(p) for p in paquetes},
    sha256_script_datos=hashlib.sha256((ROOT/'scripts/build_olist_duckdb.py').read_bytes()).hexdigest())
(R/'entorno.json').write_text(json.dumps(entorno,indent=2),encoding='utf-8')
huellas={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(R.glob('*.csv'))}
(R/'huellas_csv.json').write_text(json.dumps(huellas,indent=2),encoding='utf-8')
md=['# Auditoría de la solución','',
    f'Se conciliaron resultados mediante SQL y cálculos independientes. Los {len(MODELOS)} modelos se reajustaron en dos orígenes retirando físicamente las compras posteriores. Las siguientes comprobaciones terminaron correctamente.','',
    '| Comprobación | Resultado | Evidencia |','|---|---|---|']
md += [f'| {c["comprobacion"]} | {c["estado"]} | {c["detalle"]} |' for c in checks]
md += ['', '## Alcance de la evidencia','',
    'La ausencia de discrepancias en estas comprobaciones respalda la consistencia de la ejecución. No garantiza que el modelo funcione en otros períodos. La evaluación es retrospectiva; los errores y los intervalos tienen dependencia temporal. El corte de cobertura sigue siendo una decisión analítica.','',
    'Para repetir: `python scripts/auditar.py`, después de `python scripts/ejecutar.py`. Los detalles técnicos están en `resultados/auditoria.json`; las versiones en `resultados/entorno.json`.','']
(ROOT/'documentacion/auditoria.md').write_text('\n'.join(md),encoding='utf-8')
print(f'Auditoría completa: {len(checks)} grupos de comprobaciones.',flush=True)
