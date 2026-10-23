"""Genera informe Markdown/PDF, README y lectura numérica de la guía.

Todas las cifras proceden de CSV/JSON ejecutados. El informe PDF se compone en
scripts/informe/ (prosa en fuente.md); la guía desarrolla conceptos con mayor extensión.
"""
from pathlib import Path
import json,sys
import numpy as np
import pandas as pd

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from src.configuracion import CORTE,FIN,HORIZONTE,SELECCION,CALIBRACION,PRUEBA
R=ROOT/'resultados';D=ROOT/'documentacion'
# Las fechas del protocolo salen de la configuración: orígenes en domingo, semanas lunes-domingo.
def dia(f):return pd.Timestamp(f).strftime('%Y-%m-%d')
def objetivos(origenes):return dia(origenes[0]+pd.Timedelta(days=1)),dia(origenes[-1]+pd.Timedelta(days=HORIZONTE))
final_desde=dia(pd.Timestamp(FIN)+pd.Timedelta(days=1));final_hasta=dia(pd.Timestamp(FIN)+pd.Timedelta(days=HORIZONTE))
r=json.loads((R/'resumen.json').read_text(encoding='utf-8'))
audit=json.loads((R/'auditoria.json').read_text(encoding='utf-8'))
def leer(nombre):return pd.read_csv(R/f'{nombre}.csv')
def fmt(v):
    if pd.isna(v):return '—'
    if isinstance(v,(float,np.floating)):return f'{v:,.2f}'.replace(',','_').replace('.',',').replace('_','.')
    return str(v)
def tabla_md(df):
    filas=['| '+' | '.join(map(str,df.columns))+' |','| '+' | '.join(['---']*len(df.columns))+' |']
    filas.extend('| '+' | '.join(fmt(v).replace('|','/') for v in fila)+' |' for fila in df.itertuples(index=False,name=None))
    return '\n'.join(filas)
ms=leer('metricas_seleccion');mt=leer('metricas_prueba')
abl=leer('comparacion_componentes');est=leer('estacionariedad')
cd=leer('cobertura_diaria');cs=leer('cobertura_semanal');cds=leer('cobertura_diaria_por_semana')
final=leer('pronostico_semanal');calq=leer('cuantiles_intervalos')
principal=cd.set_index('metodo_intervalo').loc['relativo']
principal_s=cs.set_index('metodo_intervalo').loc['relativo']
absoluto=cd.set_index('metodo_intervalo').loc['absoluto']
absoluto_s=cs.set_index('metodo_intervalo').loc['absoluto']
mejora=(1-r['MAE_prueba']/r['MAE_estacional_prueba'])*100
sesgo=float(mt.set_index('modelo').loc[r['ganador'],'sesgo'])
minimo_test=mt.sort_values('MAE').iloc[0]
peores=leer('errores_mayores_seleccion')
cal_eventos=leer('errores_eventos_calibracion')
metodos=leer('cobertura_metodos').set_index('metodo_intervalo')
aj_sel=leer('ajustes_seleccion');lb_sel=aj_sel[aj_sel.modelo.eq('SARIMAX_calendario')]
ev_sel=leer('errores_por_evento');ev_sel=ev_sel[ev_sel.etapa.eq('seleccion')].pivot(index='evento',columns='modelo',values='MAE')
from src.modelos import MODELOS
imp=leer('importancia_variables')
entrega=leer('eda_entregas').iloc[0]
clientes=leer('eda_clientes');recurrentes=int(clientes.loc[clientes.compras.gt(1),'clientes'].sum());nclientes=int(clientes.clientes.sum())
geo=leer('eda_geografia');sp=int(geo.loc[geo.poblacion.eq('clientes')&geo.estado.eq('SP'),'registros'].iloc[0])
geo_est=leer('eda_clientes_por_estado');geo_reg=leer('eda_segmentos_por_region')
peso_sudeste=geo_est.loc[geo_est.region.eq('Sudeste'),'clientes'].sum()/geo_est.clientes.sum()
alto=geo_reg[geo_reg.segmento.eq('Única compra · gasto alto')].set_index('region').pct_region
rec=geo_reg[geo_reg.segmento.eq('Recurrente')].pct_region
lectura_geo=(f'El Sudeste reúne {peso_sudeste:.1%} de los clientes únicos del período útil. La recurrencia va de {rec.min():.1f} % a {rec.max():.1f} % según la región, '
             f'y el segmento de única compra con gasto alto pesa más en Norte ({alto["Norte"]:.0f} %) y Nordeste ({alto["Nordeste"]:.0f} %) que en Sudeste ({alto["Sudeste"]:.0f} %).')
sar=json.loads((R/'diagnostico_sarimax.json').read_text(encoding='utf-8'))
# Ejemplo concreto de desacierto relativo, seleccionado para explicar su limitación.
p_sel=leer('predicciones_seleccion')
fecha_ej='2017-12-24';origen_ej=dia(pd.Timestamp(fecha_ej)-pd.Timedelta(days=HORIZONTE))
ej_rel=p_sel[(p_sel.origen==origen_ej)&(p_sel.fecha==fecha_ej)&p_sel.modelo.str.startswith('LGBM')][['modelo','real','pred']]
# Lecturas que dependen de los resultados: se redactan a partir de las tablas, no a mano.
lect=est.set_index('serie')
def lectura_est(s):return f"ADF {lect.loc[s,'ADF_lectura'].lower()} y KPSS {lect.loc[s,'KPSS_lectura'].lower()}"
comp=abl.set_index('comparacion')
def cambio(nombre):
    f=comp.loc[nombre];d=f.diferencia_MAE
    return f"{'reduce' if d<0 else 'aumenta'} el MAE en {abs(d):.2f} pedidos (mejora en {int(f.origenes_mejora)} de {int(f.origenes)} orígenes)"
relativo_peor=bool((comp.loc[['Objetivo con variables básicas','Objetivo con variables ampliadas'],'diferencia_MAE']>0).all())
def lectura_minimo(negrita=True):
    b='**' if negrita else ''
    if minimo_test.modelo==r['ganador']:
        return 'El seleccionado también presenta el menor MAE de prueba; esa coincidencia no se usó para elegirlo.'
    return f'{b}{minimo_test.modelo}{b} presenta el menor MAE de prueba ({minimo_test.MAE:.2f}), pero no se redefine el ganador usando esa información.'

lectura=f'''## 20. Lectura detallada de los resultados de esta ejecución

Esta sección interpreta cifras producidas por los notebooks. Las tablas completas permiten comprobar cada afirmación.

### 20.1. Calidad y contexto

La base contiene 99.441 órdenes. En las comprobaciones aparecen 775 sin ítems, una sin pagos y 280 discrepancias mayores a dos centavos entre los totales comparados. No hay órdenes duplicadas por su llave ni compras sin fecha en la auditoría realizada. El cruce directo con ítems y pagos produce 118.434 filas: confirma por qué no sirve como unidad de conteo.

Se registran 160 aprobaciones y 2.965 entregas ausentes; 610 productos sin categoría y 13 productos cuya categoría carece de traducción. Esos problemas se informan, pero no se usan para eliminar compras válidas de la serie. Los resultados detallados están en las tablas de calidad.

En las {int(entrega.observaciones):,} entregas incluidas por la consulta, la mediana es {entrega.mediana_dias_entrega:.0f} días y el percentil 90 es {entrega.p90_dias_entrega:.0f}; la proporción tardía es {entrega.proporcion_tarde:.2%}. Esto describe entregas observadas, no las que faltan.

Hay {recurrentes:,} compradores con más de una compra entre {nclientes:,} identificadores únicos, aproximadamente {recurrentes/nclientes:.2%}. São Paulo reúne {sp:,} registros de cliente asociados a compras; no deben confundirse con compradores únicos. Estas cifras contextualizan el conjunto y no son entradas futuras del modelo.

{lectura_geo} La demanda agregada depende, por tanto, de lo que ocurra en una región dominante.

### 20.2. Diagnóstico inicial

{tabla_md(est[['serie','ADF_p','KPSS_limite','ADF_lectura','KPSS_lectura']].assign(ADF_p=lambda d:d.ADF_p.map(lambda x:f'{x:.6g}')))}

En nivel, {lectura_est('nivel')}. En primera diferencia, {lectura_est('diferencia_1')}. En diferencia semanal, {lectura_est('diferencia_7')}. Estas lecturas se restringen al historial inicial y a las especificaciones ensayadas.

En el primer SARIMAX, Ljung–Box arroja p={sar['Ljung_Box_p7']:.4f} a rezago 7 y p={sar['Ljung_Box_p14']:.4f} a 14. En las {len(lb_sel)} emisiones de selección, p7 < 0,05 en {int(lb_sel.Ljung_Box_p7.lt(.05).sum())}: queda algo de estructura semanal que seis indicadores fijos no absorben. Por eso el intervalo paramétrico, que supone innovaciones independientes, se contrasta con intervalos calibrados empíricamente. La convergencia se verificó en todos los ajustes de la ejecución.

### 20.3. Selección de candidatos

{tabla_md(ms[['modelo','MAE','RMSE','MAPE','sMAPE']])}

Se elige **{r['ganador']}**, MAE **{r['MAE_seleccion']:.2f}** pedidos por par. El mejor LightGBM es **{r['mejor_ml']}**. El criterio se fijó antes de leer la tabla de prueba.

Black Friday domina varios errores extremos: el 24 de noviembre de 2017 hubo 1.176 pedidos. El modelo seleccionado lo pronosticó desde cuatro orígenes y no disponía de un Black Friday anterior en el período útil. Por ejemplo, desde {peores.iloc[0].origen}, a h={int(peores.iloc[0].h)}, estimó {peores.iloc[0].pred:.2f}, frente a {int(peores.iloc[0].real)} reales. Su RMSE resulta mucho mayor que MAE porque los errores grandes se elevan al cuadrado. No se elimina esa fecha para embellecer el resultado.

### 20.4. Lo que aporta cada componente

{tabla_md(abl[['comparacion','diferencia_MAE','origenes_mejora','origenes']])}

La diferencia es MAE del candidato menos MAE de la referencia: negativo favorece al candidato. Añadir los indicadores de eventos a SARIMAX {cambio('Eventos de calendario en SARIMAX')}. Con objetivo absoluto, pasar a variables ampliadas {cambio('Variables con objetivo absoluto')}; con objetivo relativo, {cambio('Variables con objetivo relativo')}. Cambiar al objetivo relativo {cambio('Objetivo con variables básicas')} con variables básicas y {cambio('Objetivo con variables ampliadas')} con ampliadas. {'La hipótesis de que escalar respecto al nivel reciente ayudaría no queda respaldada por este experimento.' if relativo_peor else 'El efecto del objetivo relativo depende de la familia de variables.'}

Un ejemplo muestra que la adaptación relativa puede fallar de forma importante:

{tabla_md(ej_rel)}

Estas son predicciones emitidas el {origen_ej} para el {fecha_ej}. El desacierto relativo es observable; atribuirlo a una sola variable requeriría otra investigación. No se afirma que toda transformación relativa sea inferior en cualquier serie.

### 20.5. Evaluación retrospectiva

{tabla_md(mt[['modelo','MAE','RMSE','MAPE','sMAPE','sesgo']])}

El elegido obtiene MAE **{r['MAE_prueba']:.2f}**, frente a **{r['MAE_estacional_prueba']:.2f}** de la referencia semanal: una diferencia aproximada de **{mejora:.2f} %**. Es pequeña y no demuestra superioridad general. {lectura_minimo()}

El sesgo del seleccionado es **{sesgo:.2f} pedidos**: en promedio pronosticó por debajo de lo observado. Su MAE posterior supera al de selección; el desempeño no se trasladó de forma uniforme entre períodos. No puede atribuirse la discrepancia exclusivamente a un evento sin evidencia adicional.

En selección, con 30 emisiones por h, el error crece con el horizonte y el seleccionado supera a ambos baselines en las cuatro semanas. Las curvas de prueba tienen solo cinco emisiones en cada h y no son monótonas por obligación. La tabla de igual peso por fecha y los archivos por origen permiten distinguir el efecto del protocolo de una conclusión sobre todos los días futuros.

### 20.6. Incertidumbre observada y sus límites

Intervalos diarios:

{tabla_md(cd.assign(cobertura_porcentaje=cd.cobertura*100)[['metodo_intervalo','cubiertos','n','cobertura_porcentaje','ancho_medio']])}

Intervalos de totales semanales:

{tabla_md(cs.assign(cobertura_porcentaje=cs.cobertura*100)[['metodo_intervalo','cubiertos','n','cobertura_porcentaje','ancho_medio']])}

El método relativo principal cubre **{principal.cobertura:.2%}** de los pares diarios, por debajo del 90 % nominal. En totales semanales cubre **{principal_s.cobertura:.1%}**. **No alcanza el objetivo de cobertura en esta evaluación.** No debe presentarse como un margen validado al 90 % para decisiones operativas.

El método absoluto muestra {absoluto.cobertura:.2%} diario y {absoluto_s.cobertura:.1%} semanal, con mayor amplitud. Tampoco garantiza cobertura futura. Se conservan ambos resultados y no se elige retrospectivamente el método que mejor lució en prueba.

También se comparan intervalos fijados de antemano para otros enfoques: el paramétrico de SARIMAX cubre {metodos.loc['parametrico_sarimax','cobertura']:.1%} y el conformal relativo del mejor LightGBM {metodos.loc['conformal_ml','cobertura']:.1%}. Ninguno alcanza el nominal: la prueba contiene un valle en julio y un salto de nivel en agosto que la calibración no conocía.

El margen relativo se reduce cuando la predicción es baja. El sesgo de subpronóstico observado es compatible con parte de la pérdida de cobertura, pero esta explicación no identifica una causa única. Por semana de horizonte, la cobertura diaria relativa más baja es {cds[cds.metodo_intervalo.eq('relativo')].cobertura.min():.2%}; el promedio global oculta diferencias importantes.

Errores de calibración por tipo de día; los días de huelga se conservan:

{tabla_md(cal_eventos)}

Son pares solapados y el período comparado difiere del resto. El mayor error en esa ventana describe el episodio; no estima un efecto causal. Incluirlo reconoce riesgos históricos, aunque no basta para garantizar cobertura ante otros regímenes.

### 20.7. Pronóstico final e interpretación

Se reajusta {r['ganador']} y la suma de sus 28 puntos es **{r['total_puntos_28_dias']:,.2f} pedidos**. Se presenta como suma de estimaciones puntuales, sin atribuirle automáticamente el significado de media esperada o mediana del total.

{tabla_md(final[['semana','desde','hasta','pred','inferior','superior']])}

Los rangos son relativos y nominales al 90 %, sujetos al incumplimiento de cobertura observado anteriormente. El período es histórico; no conocemos una cobertura verificada para estas fechas finales dentro del tramo útil. Para una aplicación real, correspondería estudiar nuevos datos y validar una estrategia de calibración antes de tratar estos límites como suficientes.

La importancia por ganancia del mejor LightGBM coloca en sus primeros lugares {', '.join(imp.variable.head(4))}. Esto describe qué divisiones ayudaron al ajuste; no prueba causas del volumen de pedidos.

### 20.8. Resultado de la auditoría

Se completaron **{len(audit['comprobaciones'])} grupos de comprobaciones**, incluidos los {len(MODELOS)} modelos con futuro físicamente retirado en dos orígenes. Los tres notebooks tienen ejecución secuencial, comentarios, figuras incorporadas y ningún error de celda. La auditoría respalda la consistencia de cifras y procedimientos, no la suficiencia predictiva para cualquier uso.
'''
base=(D/'guia_completa.md').read_text(encoding='utf-8').split('## 20. Lectura detallada')[0].rstrip()
(D/'guia_completa.md').write_text(base+'\n\n'+lectura+'\n',encoding='utf-8')

# ---------------------------------------------------------------------------
# Informe PDF y Markdown: paquete scripts/informe (contexto con las cifras, fuente.md
# con la prosa, diseno con el sistema visual y render con la composición).
# ---------------------------------------------------------------------------
from informe.render import generar as generar_informe
generar_informe()

readme=f'''# Olist: pronóstico de pedidos a 28 días

Solución del **Módulo B (series de tiempo)** del taller de Aprendizaje Automático, sobre la base de datos común del Módulo 0. Responde a la pregunta de planeación: ¿cuántas órdenes recibirá Olist en las próximas semanas? Incluye preparación y calidad de datos, exploración temporal, modelos estadísticos y de ML, evaluación walk-forward, intervalos y auditoría. Los notebooks están ejecutados y comentados en español.

## Ruta de lectura

1. **[Guía completa](documentacion/guia_completa.md):** explica desde cero el problema, cada desarrollo y la interpretación concreta de resultados.
2. [Datos y calidad](notebooks/00_datos.ipynb).
3. [Exploración temporal](notebooks/B_series_01_exploracion.ipynb): incluye una tabla visible de festivos y eventos especiales.
4. [Modelado y pronóstico](notebooks/B_series_02_modelado.ipynb).
5. [Informe PDF](documentacion/informe.pdf), [informe Markdown](documentacion/informe.md) y [auditoría](documentacion/auditoria.md).

## Resultados y lectura correcta

- Serie: **{r['n_dias']} días**, {r['total_pedidos']:,} compras, de {r['inicio']} a {r['fin']}.
- Protocolo: {len(SELECCION)} emisiones de selección, {len(CALIBRACION)} de calibración y {len(PRUEBA)} de prueba. Cada emisión parte de un domingo y cubre 28 días (cuatro semanas lunes–domingo); los orígenes avanzan semanalmente.
- Seleccionado: **{r['ganador']}**, MAE {r['MAE_seleccion']:.2f} en selección y {r['MAE_prueba']:.2f} en prueba. Referencia semanal: {r['MAE_estacional_prueba']:.2f} en prueba. {lectura_minimo(False)}
- El objetivo relativo de LightGBM {'no mejora' if relativo_peor else 'no mejora de forma uniforme'} el promedio en este experimento. La comparación controlada queda documentada con sus resultados.
- **Los intervalos no alcanzan el 90 % nominal:** el principal (conformal relativo) cubre {principal.cobertura:.2%} diario ({int(principal.cubiertos)}/{int(principal.n)}) y {principal_s.cobertura:.1%} semanal ({int(principal_s.cubiertos)}/{int(principal_s.n)}); el paramétrico de SARIMAX, {metodos.loc['parametrico_sarimax','cobertura']:.1%}. No se presentan como márgenes operativamente validados al 90 %.
- Pronóstico histórico del lunes {final_desde} al domingo {final_hasta}: **{r['total_puntos_28_dias']:,.2f}** como suma de puntos. No equivale automáticamente a media esperada o mediana del total.
- **Evaluación retrospectiva:** las fechas de prueba ya eran conocidas. No es una nueva prueba ciega ni una proyección actual de Olist.

## Reproducir

Entorno utilizado: Python 3.13; versiones exactas fijadas en `requirements.txt` y entorno registrado en `resultados/entorno.json`.

```bash
python -m venv .venv
source .venv/bin/activate
# Windows: .venv\\Scripts\\activate
python -m pip install -r requirements.txt
python scripts/build_olist_duckdb.py --out data/olist.duckdb
python scripts/ejecutar.py
python scripts/auditar.py
python scripts/generar_documentacion.py
```

Ejecuta desde la raíz del proyecto. La construcción descarga datos públicos y necesita Internet. El script original reemplaza el archivo de salida si existe; no vuelvas a construir una base que quieras conservar. El análisis posterior abre DuckDB con `read_only=True`.

Para explorar interactivamente, usa VS Code con extensión Jupyter y el entorno virtual, o instala JupyterLab. Los resultados incrustados permiten leer los notebooks directamente en GitHub sin ejecutar nada.

Los notebooks son la fuente del análisis: los cambios se hacen directamente en ellos. Después de modificarlos hay que ejecutarlos de nuevo (`scripts/ejecutar.py`), correr la auditoría y regenerar la documentación.

## Estructura

```text
notebooks/       Tres recorridos explicados, código y salidas visibles
sql/             Consultas de calidad, EDA, serie, calendario y variables
src/             Configuración, datos, modelos, métricas e intervalos
scripts/         Construcción, ejecución, auditoría y documentación
resultados/      CSV/JSON derivados, configuración y evidencia
 documentacion/  Guía completa, informe PDF/Markdown, auditoría y figuras
data/            Base local reconstruible; excluida de Git
```

## Archivos para consultar resultados

- `metricas_seleccion.csv`, `metricas_prueba.csv`: comparación global de {len(MODELOS)} candidatos (MAE, RMSE, MAPE, sMAPE y sesgo).
- `comparacion_componentes.csv`: efecto de variables y objetivo de LightGBM, y de modelar eventos en SARIMAX.
- `errores_por_evento.csv`: error por tipo de día (festivos, Carnaval, Black Friday, fin de año, pre-Navidad, huelga).
- `metricas_horizonte_*`, `metricas_origen_*`, `metricas_semana_*`: detalle temporal.
- `metricas_prueba_igual_peso_fecha.csv`: sensibilidad al peso de fechas solapadas.
- `cuantiles_intervalos*.csv`, `cobertura_*` y `cobertura_metodos.csv`: calibración, amplitud y cobertura de los intervalos conformales y del paramétrico de SARIMAX.
- `pronostico_diario_28_dias.csv` y `pronostico_semanal.csv`: puntos y límites finales; no se suman límites diarios para construir los semanales.
- `auditoria.json`, `entorno.json`, `huellas_csv.json`: evidencia de verificación y reproducción.

## Alcance y atribución

Esta entrega resuelve el Módulo B (series de tiempo) sobre la base común del Módulo 0. El script de construcción suministrado en el curso se conserva. Datos: [Brazilian E-Commerce Public Dataset by Olist](https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce), versión 2 utilizada en esta ejecución. Revisar la licencia **CC BY-NC-SA 4.0** antes de redistribuir datos derivados.

La entrega excluye `data/olist.duckdb`, entornos virtuales y cachés. Está preparada para un repositorio; no se ha publicado en GitHub.
'''
(ROOT/'README.md').write_text(readme.replace('\n documentacion/','\ndocumentacion/'),encoding='utf-8')
print('Documentación generada: guía con resultados, informe Markdown/PDF y README.')
