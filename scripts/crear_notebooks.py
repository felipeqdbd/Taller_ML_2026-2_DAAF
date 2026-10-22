"""Fuente de los tres notebooks didácticos. Regenerarlos borra sus salidas.

Después de editar esta fuente: python scripts/crear_notebooks.py y ejecutar.py.
La entrega ya contiene notebooks ejecutados; no hace falta regenerarlos al leer.
"""
from pathlib import Path
import nbformat as nbf
ROOT=Path(__file__).resolve().parents[1]

def guardar(nombre,celdas):
    nb=nbf.v4.new_notebook(cells=[nbf.v4.new_markdown_cell(s) if t=='m'
                               else nbf.v4.new_code_cell(s) for t,s in celdas])
    nb.metadata.kernelspec={'display_name':'Python 3','language':'python','name':'python3'}
    nb.metadata.language_info={'name':'python','version':'3.12'}
    nbf.write(nb,ROOT/'notebooks'/nombre)

setup='''# La ruta funciona tanto al abrir notebooks/ como desde la raíz del proyecto.
from pathlib import Path
import sys, json
ROOT=Path.cwd() if (Path.cwd()/'sql').exists() else Path.cwd().parent
sys.path.insert(0,str(ROOT))
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from IPython.display import display, Markdown
from src.configuracion import INICIO, CORTE, FIN, SELECCION, CALIBRACION, PRUEBA, NIVEL, particiones
from src.datos import conectar, consultar, preparar, exportar
pd.set_option('display.max_columns',20)
pd.set_option('display.max_rows',35)
plt.rcParams.update({'figure.figsize':(12,4),'axes.grid':True,'axes.spines.top':False,'axes.spines.right':False})
(ROOT/'resultados').mkdir(exist_ok=True)
(ROOT/'documentacion/figuras').mkdir(parents=True,exist_ok=True)
con=conectar()  # read_only=True: el análisis no escribe en la base original.
def figura(nombre):
    plt.tight_layout()
    plt.savefig(ROOT/'documentacion/figuras'/f'{nombre}.png',dpi=140,bbox_inches='tight')
    plt.show()
def mostrar(tabla, titulo, nota=None):
    """Imprime un título en lenguaje natural antes de la tabla: así cada salida se entiende sin leer el código."""
    print(f'\\n■ {titulo}')
    if nota: print(f'  {nota}')
    display(tabla)
'''

guardar('00_datos_y_calidad.ipynb',[
('m','''# 0. Comprender y preparar los datos de Olist

**Pregunta del proyecto:** al cierre de un día, ¿cuántas órdenes de compra recibirá Olist cada uno de los próximos 28 días?

Desarrollamos el Módulo 0 y el Módulo B del taller. La unidad es una **orden de compra**; la fecha relevante es `order_purchase_timestamp`. Los modelos de clasificación, segmentación y la extensión opcional por categorías o estados quedan fuera del alcance.

Este notebook explica las tablas, comprueba su calidad y construye una serie diaria. El notebook 01 estudia los patrones temporales y el 02 entrena y evalúa los modelos. Ejecuta las celdas en orden; los resultados están guardados para leerlos también en GitHub.'''),
('c',setup),
('m','''## 1. Granularidad: qué representa una fila

- `orders`: una orden identificada por `order_id`.
- `order_items`: un artículo dentro de una orden; la llave es `(order_id, order_item_id)`.
- `order_payments`: un registro de pago; puede haber varios por orden.
- `order_reviews`: reseñas; un `review_id` repetido merece inspección, pero no prueba que dos filas completas sean idénticas.
- `customers`: `customer_id` identifica el registro asociado a una compra. `customer_unique_id` permite reconocer al mismo comprador entre órdenes.
- `geolocation`: varias coordenadas pueden compartir un prefijo postal.

**Ejemplo:** una compra de tres artículos sigue siendo una sola orden. Contar filas después de unir órdenes con artículos la contaría tres veces. Si además tiene dos pagos, una unión directa puede generar seis filas. Por eso el objetivo sale directamente de `orders`.'''),
('c','''# SQL consulta las llaves reales y cuantifica el efecto de uniones 1:N.
mostrar(con.sql('SHOW TABLES').df(),'Tablas disponibles en olist.duckdb',
        'Una tabla por archivo del dataset, cargadas sin limpiar.')
llaves=consultar(con,'llaves.sql'); exportar(llaves,'llaves')
mostrar(llaves,'Unicidad de la llave candidata de cada tabla',
        'repetidos > 0 indica que esa columna no identifica una fila por sí sola.')
relaciones=consultar(con,'relaciones.sql'); exportar(relaciones,'relaciones')
mostrar(relaciones,'Filas que produce unir orders con ítems y pagos (relaciones 1:N)',
        'Si filas_join_* supera a ordenes, contar filas después del JOIN sobrestima las compras.')
assert llaves.loc[llaves.tabla.eq('orders'),'repetidos'].iloc[0]==0'''),
('m','''## 2. Calidad y decisiones de tratamiento

Comprobamos fechas imposibles, ausencia de ítems/pagos, valores faltantes, relaciones huérfanas y conciliación monetaria. Primero sumamos ítems y pagos **por separado por orden**; después los unimos.

Una entrega ausente puede ser coherente con una orden cancelada o pendiente. Una discrepancia monetaria requiere investigación, pero no significa que la compra nunca ocurrió. No eliminamos órdenes por problemas que no invalidan su fecha ni su identidad. La serie incluye todos los estados finales porque el objetivo es demanda recibida, no entregas completadas.'''),
('c','''# Cada tabla queda exportada para que la conclusión pueda verificarse.
for archivo,nombre,titulo,nota in [
    ('calidad.sql','calidad','Calidad de órdenes: fechas, ítems, pagos y conciliación monetaria',
     'Conteo de órdenes que presentan cada problema.'),
    ('calidad_extra.sql','calidad_extra','Faltantes y relaciones huérfanas entre tablas',
     'Nulos en fechas y categorías, prefijos sin geolocalización e ítems sin orden/producto/vendedor.'),
    ('estados.sql','estados','Órdenes por estado final (order_status)',None)]:
    tabla=consultar(con,archivo)
    mostrar(tabla,titulo,nota); exportar(tabla,nombre)
calidad=consultar(con,'calidad.sql').iloc[0]
assert calidad.compras_sin_fecha==0 and calidad.ids_duplicados==0
print(f"\\nHay {int(calidad.ordenes):,} órdenes; {int(calidad.sin_items)} sin ítems y {int(calidad.sin_pagos)} sin pagos.")
print('Estas ausencias se documentan y no invalidan por sí mismas el conteo de compras.')'''),
('m','''## 3. Cobertura: distinguir ausencia de registros y demanda cero

Antes de entrenar debemos definir qué tramo representa una actividad suficientemente continua. La cobertura continua va de **2017-02-01 a 2018-08-21**. La actividad inicial es escasa; en el extremo final hay un descenso de registros y observaciones aisladas posteriores.

Este corte es una decisión de cobertura. Las tablas por sí solas **no demuestran** si el descenso final es comercial, administrativo o una limitación de extracción. Por tanto, los resultados son condicionales al tramo elegido. No se elige el corte buscando el menor error.

La inspección de cobertura usa toda la base para definir el universo del ejercicio; el diagnóstico que informa los modelos se limitará al historial anterior a la primera validación. Como estas fechas ya se han examinado, la evaluación completa es retrospectiva.'''),
('c','''# El calendario mensual incluye incluso meses sin órdenes.
cobertura=consultar(con,'cobertura.sql'); exportar(cobertura,'cobertura_mensual')
mostrar(cobertura,'Cobertura mensual de toda la base',
        'Órdenes y días con compras por mes; un mes con pocos días activos no es un mes de demanda normal.')
cobertura.plot.bar(x='mes',y='ordenes',legend=False,title='Cobertura mensual del conjunto completo',rot=65)
plt.ylabel('Órdenes'); figura('cobertura_mensual')
cola=consultar(con,'cola.sql',['2018-08-01']); exportar(cola,'cobertura_final')
mostrar(cola,'Órdenes por día desde 2018-08-01: caída de registros al final de la base',
        f'Justifica el corte de cobertura en {CORTE}.')'''),
('m','''## 4. Construir una observación por día mediante SQL

La consulta `serie_diaria.sql` genera todas las fechas entre los límites, cuenta compras por día y une ambas tablas. Dentro de este tramo, una fecha sin órdenes se representa con cero.

Completar el calendario es esencial: un rezago de siete filas debe representar siete días. Sin esa regularidad, una media móvil de siete filas podría cubrir más de una semana. Fuera del tramo seleccionado no convertimos automáticamente la ausencia de registros en cero.

**Corte en domingo.** La consulta recibe la fecha de corte de cobertura como parámetro (`?`) y termina la serie en el **último domingo anterior o igual** a esa fecha (`corte − dayofweek(corte)`). Con el corte 2018-08-21 (martes) la serie llega al domingo 2018-08-19. Así cada origen de pronóstico cierra una semana completa y los 28 días siguientes forman cuatro semanas **lunes–domingo**; los orígenes de selección, calibración y prueba en `src/configuracion.py` también son domingos.'''),
('c','''# Las fechas se pasan como parámetros; no se concatenan dentro de la consulta.
# SQL recorta la serie al último domingo <= CORTE.
serie=consultar(con,'serie_diaria.sql',[INICIO,CORTE])
assert serie.fecha.is_unique and serie.y.ge(0).all()
assert serie.fecha.diff().dropna().eq(pd.Timedelta(days=1)).all()
assert serie.fecha.max()==pd.Timestamp(FIN) and serie.fecha.max().dayofweek==6  # termina en domingo
exportar(serie,'serie_diaria'); con.register('serie',serie)
resumen=con.sql('SELECT min(fecha) desde,max(fecha) hasta,dayname(max(fecha)) dia_final,count(*) dias,sum(y) pedidos,min(y) minimo,max(y) maximo,count(*) FILTER(WHERE y=0) dias_cero FROM serie').df()
mostrar(resumen,'Resumen de la serie diaria del período útil',
        f'Corte de cobertura {CORTE}; la serie termina el domingo {FIN}.')
exportar(resumen,'resumen_serie')
serie.plot(x='fecha',y='y',legend=False,title='Órdenes compradas por día: período útil')
plt.ylabel('Órdenes/día'); figura('serie_diaria')
print('Un pico es una observación que debemos explicar; no se borra automáticamente.')'''),
('m','''## 5. Exploración común: clientes, geografía y entregas

Estas tablas describen el contexto del negocio. Los tiempos de entrega se calculan solo donde existen las fechas necesarias, y los retrasos se miden en días calendario frente a la fecha estimada.

Los compradores recurrentes se cuentan mediante `customer_unique_id`. La concentración geográfica describe dónde se compra, pero no demuestra por sí sola la causa de una variación temporal. Los atributos finales de entrega no entran al modelo de compras futuras.'''),
('c','''# Lecturas, filtros, uniones y agregaciones de datos crudos permanecen en SQL.
for archivo,nombre,titulo,nota in [
    ('eda_entregas.sql','eda_entregas','Tiempos de entrega y proporción de órdenes tardías',
     'Solo órdenes entregadas; el retraso se mide en días calendario frente a la fecha estimada.'),
    ('eda_geografia.sql','eda_geografia','Registros de clientes y vendedores por estado',
     'customers cuenta customer_id (un registro por orden), no personas: la sección 5.1 usa customer_unique_id.'),
    ('eda_clientes.sql','eda_clientes','Clientes reales (customer_unique_id) según su número de compras',
     'Muestra cuántas personas compran una, dos o más veces.'),
    ('eda_semanal.sql','eda_semanal','Órdenes por semana en toda la base',
     'Cada semana inicia el lunes (date_trunc week), igual que las semanas de pronóstico.')]:
    tabla=consultar(con,archivo); mostrar(tabla,titulo,nota); exportar(tabla,nombre)
distribuciones=consultar(con,'eda_distribuciones.sql'); exportar(distribuciones,'distribuciones_entrega')
fig,axes=plt.subplots(1,2,figsize=(13,4))
for eje,(tipo,g) in zip(axes,distribuciones.groupby('tipo',sort=False)):
    g.plot.bar(x='intervalo',y='ordenes',ax=eje,legend=False,title=tipo,rot=35)
    eje.set_ylabel('Órdenes')
figura('distribuciones_entrega')'''),
('m','''### 5.1 Geografía del cliente: dónde compran y qué tipo de cliente predomina

La tabla `customers` tiene un registro por orden; para hablar de **personas** agregamos por `customer_unique_id`. Si alguien compró desde varios estados, se le asigna el de su compra más reciente. Solo se usan compras del período útil (las mismas fechas de la serie, pasadas como parámetros).

- **Mapa.** `geolocation` tiene varias coordenadas por prefijo postal: se promedian por prefijo **antes** de unir (evita multiplicar filas) y se descartan coordenadas fuera de Brasil.
- **Segmentos descriptivos.** *Recurrente* (2 o más compras), *Única compra · gasto alto* (gasto ≥ percentil 75 de todos los clientes) y *Única compra · gasto bajo-medio*. Los pagos se suman por orden antes del cruce porque `order_payments` es 1:N. No es la segmentación del Módulo C: solo describe la composición de la demanda por zona.

Para la serie de tiempo esto importa porque la demanda total es una suma de regiones muy desiguales: lo que pase en la región dominante explica buena parte de los picos y caídas.'''),
('c',"""# SQL lee, une y agrega por prefijo, estado y región; pandas y matplotlib solo dan forma y dibujan.
from matplotlib.colors import LinearSegmentedColormap, LogNorm
mapa=consultar(con,'eda_mapa_clientes.sql',[INICIO,FIN]); exportar(mapa,'eda_mapa_clientes')
segmentos=consultar(con,'eda_segmentos_region.sql',[INICIO,FIN]); exportar(segmentos,'eda_segmentos_region')
con.register('mapa',mapa); con.register('segmentos',segmentos)
por_region=con.sql('''SELECT region,segmento,sum(clientes) clientes,
 round(100*sum(clientes)/sum(sum(clientes)) OVER (PARTITION BY region),1) pct_region,
 round(sum(gasto_promedio*clientes)/sum(clientes),2) gasto_promedio
 FROM segmentos GROUP BY 1,2 ORDER BY 1,2''').df()
por_estado=con.sql('''SELECT estado,any_value(region) region,sum(clientes) clientes,
 round(100*coalesce(sum(clientes) FILTER(WHERE segmento='Recurrente'),0)/sum(clientes),2) pct_recurrentes,
 round(sum(gasto_promedio*clientes)/sum(clientes),2) gasto_promedio
 FROM segmentos GROUP BY 1 ORDER BY clientes DESC''').df()
exportar(por_region,'eda_segmentos_por_region'); exportar(por_estado,'eda_clientes_por_estado')
mostrar(por_region,'Segmentos de clientes por región de Brasil',
        'pct_region = participación del segmento dentro de la región; gasto_promedio en BRL por cliente.')
mostrar(por_estado,'Clientes únicos, recurrencia y gasto promedio por estado',
        'Ordenado de mayor a menor número de clientes.')

# Mapa: cada punto es un prefijo postal; el color (escala log) indica cuántos clientes compran desde allí.
azules=LinearSegmentedColormap.from_list('azules',['#cde2fb','#86b6ef','#2a78d6','#1c5cab','#0d366b'])
etiquetas=con.sql('''SELECT estado,sum(lng*clientes)/sum(clientes) lng,sum(lat*clientes)/sum(clientes) lat
 FROM mapa GROUP BY 1 ORDER BY sum(clientes) DESC LIMIT 6''').df()
fig,ax=plt.subplots(figsize=(7.5,7.5))
puntos=ax.scatter(mapa.lng,mapa.lat,c=mapa.clientes,s=3+mapa.clientes**0.5,cmap=azules,norm=LogNorm(),linewidths=0)
for fila in etiquetas.itertuples():
    ax.annotate(fila.estado,(fila.lng,fila.lat),xytext=(8,8),textcoords='offset points',
                fontsize=10,fontweight='bold',color='#0b0b0b')
ax.set_aspect('equal'); ax.grid(False)
ax.set(xlabel='Longitud',ylabel='Latitud',title='¿Desde dónde compran los clientes? (prefijos postales, período útil)')
fig.colorbar(puntos,ax=ax,shrink=0.6,label='Clientes únicos por prefijo (escala log)')
figura('mapa_clientes')

# Barras: volumen por estado (izquierda) y composición de segmentos por región (derecha, 100 %).
nombres=['Única compra · gasto bajo-medio','Única compra · gasto alto','Recurrente']
colores=['#2a78d6','#eb6834','#1baf7a']
regiones=['Sul','Sudeste','Centro-Oeste','Nordeste','Norte']  # de sur a norte: Norte queda arriba
fig,(ax1,ax2)=plt.subplots(1,2,figsize=(15,7.5),gridspec_kw={'width_ratios':[1,1.3]})
orden=por_estado.sort_values('clientes')
ax1.barh(orden.estado+' · '+orden.region,orden.clientes,color='#2a78d6',height=0.7)
for y_,v in list(enumerate(orden.clientes))[-3:]:
    ax1.text(v,y_,f' {v:,.0f}',va='center',fontsize=9,color='#52514e')
ax1.set(title='Clientes únicos por estado',xlabel='Clientes únicos'); ax1.grid(axis='y',visible=False)
tabla=por_region.pivot(index='region',columns='segmento',values='pct_region').reindex(regiones)[nombres]
izquierda=np.zeros(len(tabla))
for nombre,color in zip(nombres,colores):
    ancho=tabla[nombre].to_numpy()
    ax2.barh(tabla.index,ancho,left=izquierda,color=color,edgecolor='white',linewidth=2,height=0.6,label=nombre)
    for y_,(x0,w) in enumerate(zip(izquierda,ancho)):
        if w>=6: ax2.text(x0+w/2,y_,f'{w:.0f}%',ha='center',va='center',fontsize=10,color='#0b0b0b')
    izquierda+=ancho
for y_,pct in enumerate(tabla['Recurrente']):
    ax2.text(101,y_,f'recurrentes {pct:.1f}%',va='center',fontsize=9,color='#52514e')
ax2.set(xlim=(0,122),xticks=range(0,101,20),xlabel='% de clientes de la región',title='Segmentos de clientes por región')
ax2.grid(axis='y',visible=False)
ax2.legend(loc='upper center',bbox_to_anchor=(0.45,-0.09),ncol=3,frameon=False)
figura('segmentos_region')

sudeste=con.execute("SELECT round(100*sum(clientes) FILTER(WHERE region='Sudeste')/sum(clientes),1) FROM segmentos").fetchone()[0]
print(f'El Sudeste concentra el {sudeste}% de los clientes únicos del período útil.')
print('La demanda diaria agregada está dominada por esa región: un choque local allí mueve la serie completa.')
print('En Norte y Nordeste pesa más el segmento de gasto alto (el flete encarece la compra lejos de los vendedores);')
print('la recurrencia es baja (≈3 %) en todas las regiones, así que la demanda depende de captar compradores nuevos.')
con.close()"""),
('m','''## 6. Comprobar que entendimos

**¿Por qué no usamos solamente órdenes entregadas?** Porque su estado final depende de hechos posteriores a la compra y definiría otro objetivo: compras que terminaron entregadas.

**¿Por qué un pago faltante no obliga a borrar una compra?** Porque estamos contando órdenes registradas con fecha válida, no calculando ingresos cobrados.

**¿Qué sale de este notebook?** Una serie diaria regular, una decisión de cobertura explícita y un inventario de calidad. Todavía no hemos elegido un modelo ni atribuido causas a los picos.''')])

guardar('01_exploracion_temporal.ipynb',[
('m','''# 1. Aprender a leer una serie de tiempo

Una serie de tiempo conserva el orden de los datos. Aquí cada valor es el número de órdenes recibidas en una fecha. Buscamos nivel, tendencia, patrón semanal y episodios extraordinarios.

El diagnóstico se limita a **2017-02-01 a 2017-07-25**, información disponible antes de la primera ventana de selección. Los gráficos de este notebook no observan la prueba para decidir especificaciones.'''),
('c',setup+'''\nserie,calendario,variables=preparar(con)
y=serie.set_index('fecha').y.asfreq('D')
diagnostico=y.loc[:SELECCION[0]]
print(f'Diagnóstico: {len(diagnostico)} días, hasta {diagnostico.index[-1].date()}.')'''),
('m','''## 1. Separar el tiempo antes de estudiar el modelo

Una **fecha de origen** es el último día observado, al cierre del cual emitimos un pronóstico. El horizonte `h` cuenta cuántos días adelante predecimos.

Las emisiones se hacen cada martes y cubren 28 días. Hay tres funciones distintas: selección elige el modelo; calibración estima márgenes de error; prueba describe su desempeño posterior. Sus fechas objetivo no se mezclan entre etapas.

Dentro de cada etapa hay solapamiento: una fecha puede tener pronósticos emitidos con distintas anticipaciones. Es una simulación operativa válida, pero las predicciones no son observaciones independientes. Los saltos entre los últimos orígenes de una etapa y los primeros de la siguiente evitan que sus objetivos se crucen.'''),
('c','''# Las fronteras son parte del diseño, no el resultado de probar modelos.
partes=particiones(); exportar(partes,'particiones')
resumen=partes.groupby('etapa',sort=False).agg(emisiones=('origen','size'),
    primer_origen=('origen','min'),ultimo_origen=('origen','max'),
    objetivos_desde=('desde','min'),objetivos_hasta=('hasta','max'))
display(resumen)
assert partes[partes.etapa.eq('seleccion')].hasta.max()<partes[partes.etapa.eq('calibracion')].desde.min()
assert partes[partes.etapa.eq('calibracion')].hasta.max()<partes[partes.etapa.eq('prueba')].desde.min()
fig,ax=plt.subplots(figsize=(12,3))
for i,etapa in enumerate(['seleccion','calibracion','prueba']):
    g=partes[partes.etapa.eq(etapa)]
    ax.barh(i,(g.hasta.max()-g.desde.min()).days+1,left=g.desde.min(),height=.55,label=etapa)
ax.set_yticks(range(3),['Selección','Calibración','Prueba']); ax.xaxis_date()
ax.set_title('Fechas objetivo de las tres etapas'); figura('protocolo_temporal')'''),
('m','''## 2. Nivel, tendencia y patrón semanal

El **nivel** es la magnitud habitual de pedidos; la **tendencia** describe su evolución lenta. Una media móvil de 28 días suaviza fluctuaciones y usa, en esta consulta, solo el día actual y los 27 anteriores.

El patrón por día de semana compara lunes con lunes, martes con martes, etc. Las medias son descriptivas: un lunes con un evento extraordinario puede elevarlas. Por eso también mostramos medianas.'''),
('c','''# Tanto las ventanas como la agrupación por día de semana se realizan en SQL.
moviles=consultar(con,'diagnostico.sql',[str(SELECCION[0].date())])
patron=consultar(con,'patron_semanal.sql',[str(SELECCION[0].date())])
exportar(moviles,'diagnostico_inicial'); exportar(patron,'patron_semanal')
fig,ax=plt.subplots(2,1,figsize=(12,7))
moviles.plot(x='fecha',y=['y','media_7','media_28'],ax=ax[0],title='Historial y medias móviles causales')
patron.plot.bar(x='dia_semana',y=['media','mediana'],ax=ax[1],rot=0,title='1=lunes ... 7=domingo')
figura('patrones_iniciales'); display(patron)
mayor=int(patron.loc[patron.media.idxmax(),'dia_semana'])
print(f'En este historial, el día {mayor} presenta la mayor media. No prueba una relación causal.')'''),
('m','''## 3. Descomposición STL

STL representa la observación como tendencia + componente estacional + residuo. Se fija período 7 porque una semana tiene siete días. La opción robusta reduce la influencia de picos al estimar los componentes.

El residuo es lo que esta descomposición no explica. No equivale al error de un pronóstico futuro. STL puede usar vecinos posteriores dentro del tramo analizado; por ello sus componentes sirven aquí para **describir**, no como variables del modelo.'''),
('c','''# Descomponemos solo el historial inicial; no usamos STL como predictor.
from statsmodels.tsa.seasonal import STL
stl=STL(diagnostico,period=7,robust=True).fit()
fig=stl.plot(); fig.set_size_inches(12,8)
figura('stl_inicial')'''),
('m','''## 4. ACF y PACF: relaciones con el pasado

ACF mide la asociación del valor actual con valores de hace 1, 2, ... días. PACF estima la asociación adicional de un rezago después de controlar los rezagos intermedios. La persistencia y los picos cerca de múltiplos de 7 ayudan a reconocer estructura temporal.

Una tendencia puede producir autocorrelación alta aunque no exista una relación estable. Estas gráficas orientan el análisis, pero no identifican de forma infalible el orden de ARIMA.'''),
('c','''# Las barras describen dependencia del pasado y requieren interpretación.
from statsmodels.graphics.tsaplots import plot_acf,plot_pacf
fig,ax=plt.subplots(1,2,figsize=(13,4))
plot_acf(diagnostico,lags=35,ax=ax[0]); plot_pacf(diagnostico,lags=35,method='ywm',ax=ax[1])
figura('acf_pacf_inicial')'''),
('m','''## 5. ADF y KPSS: interpretar hipótesis opuestas

- ADF parte de la hipótesis de raíz unitaria. Un p pequeño aporta evidencia contra ella.
- KPSS parte de estacionariedad alrededor de un nivel. Un p pequeño aporta evidencia contra ella.

Comparamos nivel, primera diferencia y diferencia semanal. Diferenciar significa restar el pasado: `y(t)-y(t-1)` o `y(t)-y(t-7)`. Los resultados dependen del tramo, la especificación y el tamaño muestral. No prueban que todos los períodos futuros tengan la misma distribución ni eligen automáticamente un modelo.'''),
('c','''import warnings
from statsmodels.tsa.stattools import adfuller,kpss
from statsmodels.tools.sm_exceptions import InterpolationWarning
filas=[]
for nombre,s in [('nivel',diagnostico),('diferencia_1',diagnostico.diff().dropna()),
                 ('diferencia_7',diagnostico.diff(7).dropna())]:
    adf=adfuller(s,autolag='AIC',result_object=False)
    # Capturamos avisos para EXPLICAR límites de la tabla, no para ocultarlos.
    with warnings.catch_warnings(record=True) as avisos:
        warnings.simplefilter('always')
        kp=kpss(s,regression='c',nlags='auto',result_object=False)
    limite=f'{kp[1]:.4f}'
    for aviso in avisos:
        if issubclass(aviso.category,InterpolationWarning):
            limite=('<= ' if 'smaller' in str(aviso.message) else '>= ')+f'{kp[1]:.2f}'
        else:
            warnings.warn(str(aviso.message),aviso.category)
    filas.append(dict(serie=nombre,ADF_p=adf[1],KPSS_p_tabla=kp[1],KPSS_limite=limite,
        ADF_lectura='Rechaza raíz unitaria' if adf[1]<.05 else 'No rechaza raíz unitaria',
        KPSS_lectura='Rechaza estacionariedad' if kp[1]<.05 else 'No rechaza estacionariedad'))
pruebas=pd.DataFrame(filas); display(pruebas); exportar(pruebas,'estacionariedad')
print('Los símbolos <= o >= indican límites tabulados del p-valor de KPSS.')'''),
('m','''## 6. Decisiones para modelar

Compararemos una referencia constante, una referencia semanal, ETS con tendencia amortiguada, SARIMAX con calendario y cuatro variantes de LightGBM.

SARIMAX usará errores ARIMA(1,1,1) sobre `log1p(y)` y seis indicadores de día de semana. En esta especificación la repetición semanal está en los regresores; no se impone diferencia semanal adicional. Es un candidato parsimonioso fijado de antemano, no una afirmación de que sea el único orden correcto.

Los eventos conocidos por calendario incluyen festivos nacionales brasileños, Black Friday, cuatro días posteriores y fin de año. No se afirma que el calendario cubra todos los festivos locales o campañas. La huelga de mayo de 2018 se conserva y se analiza como episodio histórico; su aparición futura no se proporciona al modelo como si se conociera de antemano.

**Para explicar en clase:** el calendario futuro es información disponible; el número de compras futuras no lo es. Esa distinción permite usar el día de semana de un objetivo sin cometer fuga de información.'''),
('m','''## 7. Ver cómo se calculan las fechas especiales

Al ejecutar `preparar(con)` al inicio del notebook, [la función de datos](../src/datos.py) obtiene los festivos nacionales de Brasil con `holidays`. Después, `sql/calendario.sql` crea una fila por fecha y cuatro columnas binarias: `festivo`, `black_friday`, `post_black_friday` y `fin_anio`. **1 significa que se cumple la regla de calendario; 0, que no se cumple.**

Black Friday es el viernes siguiente al cuarto jueves de noviembre. `post_black_friday` marca sus cuatro días posteriores. `fin_anio` marca el 24–31 de diciembre y el 1 de enero. Una fecha puede tener más de un indicador: Navidad es festivo y también pertenece al período de fin de año.

La tabla siguiente muestra el resultado real del cálculo, incluidos un día de huelga y un festivo futuro respecto al último día de compras seleccionado. `pedidos_observados` se añade **solo para entender el ejemplo**; no se utiliza para crear los indicadores. En septiembre de 2018, esa columna está vacía mientras que el festivo ya se conoce.'''),
('c','''# Mostrar fechas concretas calculadas por SQL y sus compras, cuando existen.
calendario_ejemplos=consultar(con,'ejemplos_calendario.sql')
display(calendario_ejemplos)
exportar(calendario_ejemplos,'ejemplos_calendario')
# Resumimos cuántos días activa cada indicador; pueden coincidir en una fecha.
resumen_calendario=consultar(con,'resumen_calendario.sql')
display(resumen_calendario)
exportar(resumen_calendario,'resumen_calendario')
print('Black Friday 2017 marca 1; el día siguiente marca post_black_friday=1.')
print('El 21/05/2018 no recibe un indicador de huelga futura.')'''),
('c','''# Cerramos el acceso de solo lectura; el siguiente notebook es autónomo.
con.close()
print('Continúa con 02_modelado_y_pronostico.ipynb.')''')])

guardar('02_modelado_y_pronostico.ipynb',[
('m','''# 2. Modelar, evaluar y pronosticar 28 días

**Objetivo:** producir una estimación diaria y cuantificar incertidumbre a partir de compras históricas.

Secuencia: variables causales → candidatos → selección temporal → calibración independiente de la selección → evaluación retrospectiva → reajuste final.

Cada tabla y figura se exporta a `resultados/` o `documentacion/figuras/`. Las funciones comentadas están en `src/modelos.py` y `src/evaluacion.py`; el notebook explica su significado y muestra las entradas y salidas. Los datos de prueba ya han sido examinados en el contexto de este ejercicio: el protocolo respeta el tiempo, pero **no constituye una nueva evaluación ciega**.'''),
('c',setup+'''\nfrom src.modelos import MODELOS, CONFIG_ML, BASICAS, AMPLIAS, predecir, evaluar, matrices
from src.evaluacion import metricas, calibrar, aplicar_intervalos, cobertura, totales_semanales
serie,calendario,variables=preparar(con)
y=serie.set_index('fecha').y.asfreq('D')
exportar(particiones(),'particiones')
# Manifestamos decisiones antes de ajustar cualquier candidato.
protocolo=dict(inicio=INICIO,fin=FIN,nivel=NIVEL,modelos=MODELOS,config_ml=CONFIG_ML,
    criterio='MAE sobre pares origen-horizonte de selección; desempate alfabético',
    intervalo_principal='relativo; absoluto como análisis paralelo sin selección en prueba',
    interpretacion='Evaluación retrospectiva de datos previamente conocidos')
(ROOT/'resultados/protocolo.json').write_text(json.dumps(protocolo,ensure_ascii=False,indent=2),encoding='utf-8')
print(f'{len(serie)} días; {len(variables)} pares origen-horizonte para ML.')
print(f'{len(SELECCION)} emisiones de selección, {len(CALIBRACION)} de calibración y {len(PRUEBA)} de prueba.')'''),
('m','''## 1. Convertir la serie en ejemplos supervisados

Para un origen `o` y horizonte `h`, queremos aprender `historia hasta o + calendario de o+h → compras de o+h`.

Ejemplo: al cierre del martes, sabemos cuántas compras hubo ese martes. Ese valor es `lag_0`. Para predecir el miércoles, el último miércoles observado fue seis días atrás; para predecir el martes siguiente, el último martes es el origen. La consulta calcula correctamente ese desplazamiento para todos los horizontes.

Las medias móviles terminan en el origen. Las variables ampliadas incluyen los últimos siete días, la media de 91 días, relaciones de nivel, variabilidad y las últimas cuatro observaciones del mismo día de semana. Los primeros 90 días sirven como historial; todas las variantes ML usan exactamente las mismas filas para que la comparación sea controlada.'''),
('c','''# Seleccionamos un ejemplo con SQL; real es etiqueta, nunca una variable predictora.
con.register('variables',variables)
ejemplo=con.execute('''+repr('''SELECT origen,fecha,h,lag_0,media_7,media_28,media_91,
 ultimo_mismo_dia,media_4_mismo_dia,real FROM variables
 WHERE origen=CAST(? AS DATE) AND h IN (1,7,28) ORDER BY h''')+''',[str(SELECCION[0].date())]).df()
display(ejemplo); exportar(ejemplo,'ejemplo_variables')
assert 'real' not in BASICAS and 'real' not in AMPLIAS
assert not variables[BASICAS+AMPLIAS].isna().any().any()
print('La historia se fija en el origen; el día objetivo y su patrón semanal dependen de h.')'''),
('m','''### Ejemplo: los indicadores llegan al modelo

El calendario no se queda en una tabla descriptiva. `sql/features.sql` lo une a cada par origen-horizonte. Consultamos el pronóstico emitido al cierre del 21 de noviembre de 2017: en h=3, la fecha objetivo es Black Friday. La columna `real` aparece para comprobar después qué ocurrió; **no** forma parte de las entradas de LightGBM. SARIMAX toma esas mismas columnas del calendario mediante `exogenas()` en `src/modelos.py`.

La presencia de `black_friday=1` no garantiza una predicción acertada: antes de esa fecha no había otro Black Friday en el período útil para aprender su magnitud.'''),
('c','''# La consulta conserva la fecha de origen y la fecha objetivo de cada fila.
ejemplo_evento=consultar(con,'ejemplo_variables_evento.sql',
                        ['2017-11-21','2017-11-24','2017-11-28'])
display(ejemplo_evento)
exportar(ejemplo_evento,'ejemplo_variables_evento')
assert ejemplo_evento.loc[ejemplo_evento.fecha.eq(pd.Timestamp('2017-11-24')),
                          'black_friday'].iloc[0]==1
print('El calendario del objetivo se conoce; el valor real solo se consulta después para evaluar.')'''),
('m','''## 2. Evitar fuga: controlar la fecha de la etiqueta

No basta con exigir que el origen de una fila sea pasado. Si una fila emitida ayer intenta predecir dentro de 28 días, su etiqueta todavía es desconocida hoy.

Por eso, en cada ajuste se exige **`fecha_objetivo <= origen_del_ajuste`**. Las filas futuras se mantienen para obtener predicciones, pero sus valores reales no se entregan al modelo. Los notebooks pueden contener la serie completa para evaluar; las funciones de ajuste recortan estrictamente la información permitida.'''),
('c','''# Inspeccionamos el primer ajuste: las etiquetas llegan como máximo a su origen.
train,futuro=matrices(variables,SELECCION[0])
display(pd.DataFrame([dict(filas_entrenamiento=len(train),ultima_etiqueta=train.fecha.max(),
    origen_ajuste=SELECCION[0],primer_objetivo=futuro.fecha.min(),ultimo_objetivo=futuro.fecha.max())]))
assert train.fecha.max()<=SELECCION[0]
assert futuro.fecha.min()>SELECCION[0]
print('Los pares reutilizan días reales: su cantidad no equivale a observaciones independientes.')'''),
('m','''## 3. Qué aprende cada modelo

| Modelo | Regla o estructura | Para qué sirve |
|---|---|---|
| Ingenuo | Repite el último valor 28 veces | Referencia mínima |
| Estacional_7 | Repite los últimos siete días | Referencia que respeta el ciclo semanal |
| ETS_amortiguado | Nivel + tendencia amortiguada + estacionalidad de 7 días | Adaptación suave del patrón |
| SARIMAX_calendario | Logaritmo, errores ARIMA(1,1,1), calendario y día semanal | Dependencia temporal con regresores conocidos |
| LightGBM, cuatro variantes | Árboles pequeños con historia, calendario y horizonte | Relaciones no lineales y comparación controlada |

Los cuatro LightGBM usan los mismos 300 árboles, 7 hojas, tasa de aprendizaje 0,03, pérdida L1 y semilla. Cruzamos dos factores: variables básicas/ampliadas y objetivo absoluto/relativo. No hacemos una búsqueda extensa de hiperparámetros.

El objetivo absoluto es `y`. El relativo es `r = log(1+y) - log(1+media_28)`. La inversión es `y_hat = exp(r_hat) × (1+media_28) - 1`, usando siempre la media del origen. El logaritmo estabiliza escala, pero L1 en esta escala pondera los errores de manera distinta a L1 en pedidos; su utilidad debe comprobarse en pedidos.

L1 aproxima una **mediana condicional**, no automáticamente una media. La transformación inversa es monótona, pero puede dar valores negativos; el código los recorta explícitamente a cero.'''),
('c','''# Ejemplo pedagógico de ida y vuelta, independiente del entrenamiento real.
media_ejemplo=200.0; pedidos_ejemplo=220.0
r_ejemplo=np.log1p(pedidos_ejemplo)-np.log1p(media_ejemplo)
recuperado=np.expm1(r_ejemplo+np.log1p(media_ejemplo))
print(f'Media reciente: {media_ejemplo:.0f}; objetivo: {pedidos_ejemplo:.0f}; r={r_ejemplo:.4f}.')
print(f'Invirtiendo la transformación recuperamos {recuperado:.1f} pedidos.')
print(f'Variables básicas: {len(BASICAS)}. Ampliadas: {len(AMPLIAS)}.')
display(pd.DataFrame([CONFIG_ML]))'''),
('m','''## 4. Selección walk-forward: aprender del pasado y avanzar

En cada uno de los 30 orígenes se vuelve a entrenar desde cero con toda la historia permitida. Se predicen 28 días y se guardan los reales para calcular errores. Después avanzamos siete días.

El criterio principal es **MAE promedio sobre todos los pares origen-horizonte de selección**. Cada emisión tiene 28 pares, así que coincide con promediar los MAE de los orígenes. RMSE penaliza más los errores grandes; sMAPE expresa error relativo simétrico (de 0 a 200 %). Si real y predicción son cero, su contribución a sMAPE es cero.

Todas las fechas se conservan, incluidos picos. Las ventanas solapadas dan más peso a fechas centrales, pero representan distintas decisiones de pronóstico. Exportaremos también una métrica con igual peso por fecha.'''),
('c','''# Este es el bloque de mayor tiempo de ejecución: 30 × 8 ajustes.
p_sel,aj_sel=evaluar(y,variables,calendario,SELECCION,MODELOS)
exportar(p_sel,'predicciones_seleccion'); exportar(aj_sel,'ajustes_seleccion')
m_sel=metricas(p_sel).sort_values(['MAE','modelo']).reset_index(drop=True)
exportar(m_sel,'metricas_seleccion'); display(m_sel.round(3))
ganador=m_sel.iloc[0].modelo
mejor_ml=m_sel[m_sel.modelo.str.startswith('LGBM')].iloc[0].modelo
print('Modelo seleccionado exclusivamente por MAE de selección:',ganador)
print('Mejor candidato ML en selección:',mejor_ml)'''),
('m','''## 5. Identificar qué aporta cada componente

La comparación factorial permite observar el efecto de ampliar variables manteniendo el objetivo, y de expresar el objetivo en términos relativos manteniendo las variables. Una mejora corresponde al conjunto de variables ampliadas; no permite atribuirla a una sola variable sin un experimento adicional.

También calculamos diferencias de MAE por origen. Un promedio favorable no significa que el modelo gane en todos los períodos. Los orígenes se solapan; sus diferencias no se usan aquí como si fueran una muestra independiente para declarar significancia estadística.'''),
('c','''# Diferencia negativa: el segundo modelo tiene menor MAE.
por_origen=metricas(p_sel,('modelo','origen')); exportar(por_origen,'metricas_origen_seleccion')
pivote=por_origen.pivot(index='origen',columns='modelo',values='MAE')
comparaciones=[]
for referencia,candidato,idea in [
 ('LGBM_base_absoluto','LGBM_amplio_absoluto','Variables con objetivo absoluto'),
 ('LGBM_base_relativo','LGBM_amplio_relativo','Variables con objetivo relativo'),
 ('LGBM_base_absoluto','LGBM_base_relativo','Objetivo con variables básicas'),
 ('LGBM_amplio_absoluto','LGBM_amplio_relativo','Objetivo con variables ampliadas')]:
    d=pivote[candidato]-pivote[referencia]
    comparaciones.append(dict(comparacion=idea,referencia=referencia,candidato=candidato,
        diferencia_MAE=d.mean(),origenes_mejora=int((d<0).sum()),origenes=len(d)))
ablacion=pd.DataFrame(comparaciones); display(ablacion.round(3)); exportar(ablacion,'comparacion_componentes')
pivote[[ganador,'Estacional_7']].plot(title='MAE por origen: variabilidad entre períodos')
plt.ylabel('Error absoluto medio (pedidos)'); figura('mae_origen_seleccion')
# Errores grandes merecen una explicación concreta, no solo un promedio.
peores=p_sel[p_sel.modelo.eq(ganador)].assign(error=lambda d:abs(d.real-d.pred)).nlargest(8,'error')
display(peores); exportar(peores,'errores_mayores_seleccion')'''),
('m','''## 6. Revisar convergencia y residuos estadísticos

SARIMAX registra la convergencia del optimizador en cada origen. Si el primer algoritmo no converge, se aplica una segunda estrategia fijada previamente; si tampoco converge, la ejecución se detiene. Los avisos se conservan en las tablas de ajustes.

La prueba Ljung–Box examina autocorrelación residual conjunta. Un p pequeño sugiere estructura que el modelo no absorbió. Un p grande no demuestra que el modelo sea correcto. Se muestran innovaciones estandarizadas, tras descartar la inicialización, en el primer origen para que el diagnóstico no use prueba.'''),
('c','''# Ajuste del primer origen para visualizar residuos y sus límites.
from statsmodels.graphics.tsaplots import plot_acf
_,detalle_sar=predecir('SARIMAX_calendario',y,variables,calendario,SELECCION[0],detalles=True)
residuos=np.asarray(detalle_sar.pop('residuos'))
coeficientes=detalle_sar.pop('coeficientes')
(ROOT/'resultados/diagnostico_sarimax.json').write_text(json.dumps(detalle_sar,ensure_ascii=False,indent=2),encoding='utf-8')
display(aj_sel[aj_sel.modelo.eq('SARIMAX_calendario')][['origen','convergencia','optimizador','Ljung_Box_p7','Ljung_Box_p14']])
fig,ax=plt.subplots(1,2,figsize=(13,4))
ax[0].plot(residuos); ax[0].axhline(0,color='black',linewidth=.7); ax[0].set_title('Innovaciones estandarizadas: primer origen')
plot_acf(residuos,lags=28,ax=ax[1]); figura('residuos_sarimax')
print('Avisos registrados en selección:',int(aj_sel.avisos.ne('').sum()))
print('El AIC de ETS sobre pedidos no se compara directamente con SARIMAX sobre logaritmos.')'''),
('m','''## 7. Calibrar incertidumbre con una etapa reservada

El modelo ya está elegido. Ahora se reajusta en 12 orígenes posteriores que no participaron en la selección. Sus errores sirven para estimar márgenes.

Comparamos dos construcciones definidas de antemano: errores absolutos `|real-pred|` y errores relativos `|real-pred|/(1+pred)`. La principal es la relativa; la absoluta se informa como análisis paralelo sin escoger por su cobertura de prueba.

Para cada semana del horizonte ordenamos los errores y elegimos el elemento de rango `ceil((n+1)×0,90)`. En el caso diario hay 84 errores por grupo y se toma el número 77. El intervalo relativo es `pred ± q×(1+pred)`, limitado a cero por abajo.

La dependencia temporal, el solapamiento y el reajuste impiden prometer cobertura conformal exacta. El 90 % es un objetivo nominal que debemos contrastar con cobertura y amplitud observadas.'''),
('c','''# El candidato ya está fijado; estos errores solo calibran incertidumbre.
p_cal,aj_cal=evaluar(y,variables,calendario,CALIBRACION,[ganador])
exportar(p_cal,'predicciones_calibracion'); exportar(aj_cal,'ajustes_calibracion')
cal_diaria={m:calibrar(p_cal,metodo=m) for m in ['absoluto','relativo']}
cal_semanal={m:calibrar(p_cal,metodo=m,semanal=True) for m in ['absoluto','relativo']}
cuantiles=pd.concat([*cal_diaria.values(),*cal_semanal.values()],ignore_index=True)
display(cuantiles); exportar(cuantiles,'cuantiles_intervalos')'''),
('m','''## 8. Intervalos de totales semanales

Una semana operativa comprende h1–h7, la siguiente h8–h14, etc. Primero sumamos los siete valores reales y las siete predicciones; luego calculamos el error de ese **total**. Su cuantil produce un intervalo específico para la semana.

Aquí hay solo 12 residuos de total por posición semanal. Para 90 % el rango es 12: se utiliza el máximo de esos residuos. Es un cálculo finito y verificable, pero sensible a pocos episodios y a la dependencia entre emisiones.

**No sumamos límites diarios.** Por ejemplo, aunque cada intervalo diario cubra 80 %, la probabilidad de que los siete cubran a la vez puede ser muy distinta. Los intervalos semanales tampoco garantizan que las cuatro semanas queden cubiertas simultáneamente.'''),
('c','''# Agrupamos puntos y reales antes de construir márgenes para totales.
totales_cal=totales_semanales(p_cal); display(totales_cal.head(8)); exportar(totales_cal,'totales_semanales_calibracion')
assert len(totales_cal)==len(CALIBRACION)*4
print('Cada fila es un total de siete días de una emisión, no un límite diario sumado.')'''),
('m','''## 9. Prueba retrospectiva: las últimas ocho semanas útiles

Evaluamos del **27 de junio al 21 de agosto de 2018** mediante cinco emisiones. Son 140 pares por modelo y 56 fechas distintas. Los puntos centrales se pronostican hasta cuatro veces con anticipaciones diferentes.

Cada origen puede incorporar ventas de prueba que ya ocurrieron antes de esa emisión: eso reproduce un reajuste operativo legítimo. El candidato seleccionado y los cuantiles de intervalos permanecen fijados. No elegimos otro ganador por mirar esta tabla.'''),
('c','''p_test,aj_test=evaluar(y,variables,calendario,PRUEBA,MODELOS)
exportar(p_test,'predicciones_prueba'); exportar(aj_test,'ajustes_prueba')
m_test=metricas(p_test).sort_values(['MAE','modelo']); display(m_test.round(3)); exportar(m_test,'metricas_prueba')
for etapa,p in [('seleccion',p_sel),('prueba',p_test)]:
    exportar(metricas(p,('modelo','h')),f'metricas_horizonte_{etapa}')
    exportar(metricas(p.assign(semana=(p.h-1)//7+1),('modelo','semana')),f'metricas_semana_{etapa}')
    exportar(metricas(p,('modelo','origen')),f'metricas_origen_{etapa}')
# Igual peso por fecha: primero promediamos pérdidas de sus emisiones, luego fechas.
con.register('predicciones',p_test)
igual_fecha=con.sql('''+repr('''WITH diario AS (SELECT modelo,fecha,
 avg(abs(real-pred)) mae,avg(pow(real-pred,2)) mse,
 avg(CASE WHEN abs(real)+abs(pred)=0 THEN 0 ELSE 200*abs(real-pred)/(abs(real)+abs(pred)) END) smape
 FROM predicciones GROUP BY 1,2)
 SELECT modelo,avg(mae) MAE,sqrt(avg(mse)) RMSE,avg(smape) sMAPE,count(*) fechas
 FROM diario GROUP BY 1 ORDER BY MAE''')+''').df()
display(igual_fecha.round(3)); exportar(igual_fecha,'metricas_prueba_igual_peso_fecha')
peso=con.sql("SELECT fecha,count(*) emisiones FROM predicciones WHERE modelo='Estacional_7' GROUP BY fecha ORDER BY fecha").df()
exportar(peso,'peso_fechas_prueba')
print(f'Ganador fijado en selección: {ganador}. Mejor MAE observado en prueba: {m_test.iloc[0].modelo}.')'''),
('m','''## 10. Leer errores por anticipación

MAE se expresa en pedidos, RMSE también y sMAPE en porcentaje. Una curva puede subir o bajar: no imponemos que el error crezca de forma monótona con el horizonte.

Las diferencias entre horizontes también dependen de qué fechas evalúa cada uno. En este experimento cada h de prueba tiene solo cinco emisiones. Una curva irregular es esperable y no debe interpretarse como una ley general.'''),
('c','''# Comparamos representantes elegidos sin consultar su error de prueba.
representantes=list(dict.fromkeys(['Estacional_7','ETS_amortiguado','SARIMAX_calendario',mejor_ml,ganador]))
fig,ax=plt.subplots(1,3,figsize=(16,4))
por_h=metricas(p_test,('modelo','h'))
for eje,metrica in zip(ax,['MAE','RMSE','sMAPE']):
    for nombre in representantes:
        g=por_h[por_h.modelo.eq(nombre)]
        eje.plot(g.h,g[metrica],label=nombre)
    eje.set_title(metrica); eje.set_xlabel('Horizonte (días)')
ax[0].set_ylabel('Pedidos'); ax[1].set_ylabel('Pedidos'); ax[2].set_ylabel('%')
ax[2].legend(fontsize=7); figura('metricas_horizonte_prueba')
display(metricas(p_test.assign(semana=(p_test.h-1)//7+1),('modelo','semana')).round(3))'''),
('m','''## 11. Medir cobertura y amplitud

Cobertura = proporción de reales que quedaron entre los límites. Amplitud = límite superior − inferior, en pedidos. Una cobertura alta con intervalos enormes puede tener poca utilidad operativa; ambas medidas deben leerse juntas.

En diario se evalúan 140 pares dependientes; en totales semanales, 20 pares. Informamos además por semana de horizonte para que un promedio global no oculte fallos concentrados. Los cuantiles no se recalibran con estos errores de prueba.'''),
('c','''# Aplicamos cuantiles reservados: no se estiman con los errores de prueba.
seleccionado_test=p_test[p_test.modelo.eq(ganador)].copy()
i_test=pd.concat([aplicar_intervalos(seleccionado_test,cal_diaria[m]) for m in cal_diaria],ignore_index=True)
i_sem=pd.concat([aplicar_intervalos(seleccionado_test,cal_semanal[m],semanal=True) for m in cal_semanal],ignore_index=True)
exportar(i_test,'intervalos_diarios_prueba'); exportar(i_sem,'intervalos_semanales_prueba')
cov_d=cobertura(i_test); cov_s=cobertura(i_sem)
display(cov_d); display(cov_s)
exportar(cov_d,'cobertura_diaria'); exportar(cov_s,'cobertura_semanal')
exportar(cobertura(i_test,('metodo_intervalo','semana')),'cobertura_diaria_por_semana')
exportar(cobertura(i_sem,('metodo_intervalo','semana')),'cobertura_semanal_por_semana')
principal=i_test[i_test.metodo_intervalo.eq('relativo')]
fig,axes=plt.subplots(2,1,figsize=(12,7))
for eje,origen in zip(axes,[PRUEBA[0],PRUEBA[-1]]):
    g=principal[principal.origen.eq(origen)]
    eje.plot(g.fecha,g.real,label='Real'); eje.plot(g.fecha,g.pred,label='Pronóstico')
    eje.fill_between(g.fecha,g.inferior,g.superior,alpha=.2,label='Intervalo nominal 90 %')
    eje.set_title(f'Emisión del {origen.date()} — {ganador}'); eje.legend()
figura('evaluacion_intervalos')'''),
('m','''## 12. Eventos y explicaciones prudentes

Black Friday y la huelga se conservan. La primera ventana de Black Friday 2017 ocurre cuando el modelo todavía no ha observado otro Black Friday en el tramo útil: un indicador conocido no permite aprender una magnitud sin ejemplos.

La huelga se encuentra en calibración; sus errores pueden aumentar los márgenes. Es parte del riesgo histórico conservado. Los promedios de eventos y del resto se refieren a épocas distintas y no son una estimación causal del efecto de esos eventos.'''),
('c','''# Describimos períodos; esta comparación no identifica efectos causales.
eventos=consultar(con,'eventos.sql'); display(eventos); exportar(eventos,'descripcion_eventos')
con.register('p_cal',p_cal)
error_eventos=con.sql('''+repr('''SELECT CASE WHEN fecha BETWEEN DATE '2018-05-21' AND DATE '2018-05-31'
 THEN 'Ventana de huelga' ELSE 'Resto de calibración' END periodo,
 count(*) pares,count(DISTINCT fecha) fechas,avg(abs(real-pred)) MAE
 FROM p_cal GROUP BY 1 ORDER BY 1''')+''').df()
display(error_eventos); exportar(error_eventos,'errores_eventos_calibracion')'''),
('m','''## 13. Pronóstico final histórico

Reajustamos el modelo seleccionado con todo el período útil hasta el 21 de agosto de 2018 y pronosticamos del **22 de agosto al 18 de septiembre de 2018**. Es una simulación histórica, no una proyección de Olist para la actualidad.

Mantenemos los cuantiles aprendidos en calibración para conservar trazabilidad. La distribución final puede diferir: su cobertura futura es desconocida. Los puntos son continuos aunque las compras reales sean enteras; redondeamos solo para presentar, conservando decimales en los archivos.

La suma de 28 pronósticos puntuales no es automáticamente la media esperada ni la mediana del total. Los intervalos semanales se obtienen de errores de totales y no se suman para anunciar cobertura mensual.'''),
('c','''# El reajuste usa toda la historia útil; los reales futuros siguen vacíos.
origen_final=pd.Timestamp(FIN)
p_final,aj_final=predecir(ganador,y,variables,calendario,origen_final)
final=pd.DataFrame(dict(modelo=ganador,origen=origen_final,
    fecha=pd.date_range(origen_final+pd.Timedelta(days=1),periods=28),
    h=np.arange(1,29),real=np.nan,pred=p_final))
final_d=aplicar_intervalos(final,cal_diaria['relativo'])
final_s=aplicar_intervalos(final,cal_semanal['relativo'],semanal=True)
exportar(final_d,'pronostico_diario_28_dias'); exportar(final_s,'pronostico_semanal')
exportar(pd.DataFrame([aj_final]),'ajuste_final')
# Redondeamos solo columnas numéricas para presentar; los CSV conservan precisión.
vista_d=final_d[['fecha','h','pred','inferior','superior']].copy()
vista_s=final_s[['semana','desde','hasta','pred','inferior','superior']].copy()
for vista in [vista_d,vista_s]:
    vista[['pred','inferior','superior']]=vista[['pred','inferior','superior']].round(1)
    display(vista)
fig,ax=plt.subplots(figsize=(12,5))
# Usamos fechas datetime en ambas curvas para mantener la misma escala temporal.
ax.plot(y.index[-56:],y.iloc[-56:].to_numpy(),label='Historial')
ax.plot(final_d.fecha,final_d.pred,label='Pronóstico')
ax.fill_between(final_d.fecha,final_d.inferior,final_d.superior,alpha=.25,label='Intervalo diario nominal 90 %')
ax.set_title(f'Pronóstico histórico a 28 días — {ganador}'); ax.set_ylabel('Pedidos'); ax.legend()
figura('pronostico_final')
print(f'Suma de puntos a 28 días: {final.pred.sum():,.1f} pedidos.')'''),
('m','''## 14. Interpretar LightGBM sin atribuir causalidad

La importancia por ganancia resume cuánto redujeron la pérdida las divisiones que usaron cada variable. Depende de variables correlacionadas y no indica que intervenir esa variable cause más ventas.

Se muestra para el mejor candidato ML elegido en selección, incluso si el ganador global pertenece a otra familia. Esto es una explicación del modelo, no un criterio adicional para elegirlo después de la prueba.'''),
('c','''# La ganancia explica el ajuste de ML y no se interpreta como causalidad.
_,detalle_ml=predecir(mejor_ml,y,variables,calendario,origen_final,detalles=True)
importancia=pd.DataFrame(detalle_ml['importancia_gain'].items(),columns=['variable','ganancia']).sort_values('ganancia',ascending=False)
exportar(importancia,'importancia_variables'); display(importancia.head(12).round(2))
importancia.head(12).sort_values('ganancia').plot.barh(x='variable',y='ganancia',legend=False,title=f'Importancia por ganancia: {mejor_ml}')
figura('importancia_variables')'''),
('m','''## 15. Conclusiones que se derivan de los resultados

Leemos primero el criterio de selección, luego la evaluación posterior y finalmente la incertidumbre. Un ganador de selección puede perder en prueba. Una transformación relativa puede ayudar o perjudicar según la muestra. El valor del ejercicio está en comprobarlo mediante un protocolo explícito.

La auditoría adicional concilia las métricas mediante SQL, verifica las ventanas, retira físicamente el futuro para reproducir ajustes y comprueba que los notebooks estén ejecutados sin errores.'''),
('c','''# Las conclusiones se generan desde tablas para evitar cifras inconsistentes.
ms=m_sel.set_index('modelo'); mt=m_test.set_index('modelo')
cd=cov_d.set_index('metodo_intervalo').loc['relativo']
cs=cov_s.set_index('metodo_intervalo').loc['relativo']
resumen=dict(inicio=INICIO,fin=FIN,ganador=ganador,mejor_ml=mejor_ml,
    MAE_seleccion=float(ms.loc[ganador,'MAE']),MAE_prueba=float(mt.loc[ganador,'MAE']),
    MAE_estacional_prueba=float(mt.loc['Estacional_7','MAE']),
    mejor_prueba=m_test.iloc[0].modelo,cobertura_diaria=float(cd.cobertura),
    cubiertos_diarios=int(cd.cubiertos),n_diarios=int(cd.n),
    cobertura_semanal=float(cs.cobertura),cubiertos_semanales=int(cs.cubiertos),n_semanales=int(cs.n),
    total_puntos_28_dias=float(final.pred.sum()),n_dias=len(serie),total_pedidos=int(serie.y.sum()),
    interpretacion='Retrospectiva; los datos de prueba ya eran conocidos. Sin garantía de cobertura futura.')
(ROOT/'resultados/resumen.json').write_text(json.dumps(resumen,ensure_ascii=False,indent=2),encoding='utf-8')
display(Markdown(f"""**Selección:** {ganador}, MAE {resumen['MAE_seleccion']:.2f} pedidos.\n\n
**Prueba:** MAE {resumen['MAE_prueba']:.2f}; referencia semanal {resumen['MAE_estacional_prueba']:.2f}.\n\n
**Incertidumbre relativa:** cobertura diaria {cd.cobertura:.1%} ({int(cd.cubiertos)}/{int(cd.n)} pares);
semanal {cs.cobertura:.1%} ({int(cs.cubiertos)}/{int(cs.n)} totales). Nivel nominal 90 %.\n\n
**Pronóstico final:** suma de puntos {final.pred.sum():,.1f}; se debe leer junto a sus intervalos y límites históricos."""))
if cd.cobertura < NIVEL:
    print('El intervalo relativo principal NO alcanzó el 90 % nominal en prueba.')
    print('Sus límites finales son experimentales; no se presentan como cobertura futura validada.')
print('La tabla de prueba describe rendimiento posterior y no redefine la elección previa.')
con.close()'''),
('m','''## Preguntas para defender el ejercicio

1. **¿Qué se predice?** Órdenes registradas por día, a partir del cierre de un origen.
2. **¿Por qué no barajar días?** Porque permitiría que el entrenamiento conociera el futuro del ejemplo evaluado.
3. **¿Por qué filtrar fecha objetivo?** Una fila de origen pasado puede tener una etiqueta todavía futura.
4. **¿Por qué dos referencias simples?** Para saber cuánto valor añade la complejidad frente a reglas comprensibles.
5. **¿Qué significa MAE=40?** Un error absoluto promedio de 40 pedidos por par evaluado; no un máximo de 40.
6. **¿90 % garantiza cada semana?** No: es nominal y depende de estabilidad, muestra y dependencia.
7. **¿Se puede sumar un intervalo diario?** No para atribuir automáticamente la misma cobertura al total.
8. **¿El modelo ganador sirve siempre?** Su rendimiento es específico del protocolo y período; se necesita evaluación posterior y monitoreo.''')])
print('Tres notebooks generados. Ejecuta scripts/ejecutar.py para incorporar salidas.')
