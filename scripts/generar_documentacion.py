"""Genera informe Markdown/PDF, README y lectura numérica de la guía.

Todas las cifras proceden de CSV/JSON ejecutados. El PDF es una síntesis de
10 secciones; la guía desarrolla conceptos con mayor extensión.
"""
from pathlib import Path
from xml.sax.saxutils import escape
import json,sys
import numpy as np
import pandas as pd
from reportlab.platypus import SimpleDocTemplate,Paragraph,Spacer,Table,TableStyle,Image,PageBreak
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet,ParagraphStyle
from reportlab.lib.units import cm
from reportlab.lib.enums import TA_LEFT
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

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
    if isinstance(v,(float,np.floating)):return f'{v:,.2f}'
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

En el primer SARIMAX, Ljung–Box arroja p={sar['Ljung_Box_p7']:.4f} a rezago 7 y p={sar['Ljung_Box_p14']:.4f} a 14. Al umbral convencional de 5 % no se rechaza en esos dos casos, pero el primero está cerca del umbral. Esto no demuestra residuos independientes ni adecuación universal. Los demás orígenes están registrados en las tablas de ajustes; la convergencia se verificó en todos los ajustes de la ejecución.

### 20.3. Selección de candidatos

{tabla_md(ms[['modelo','MAE','RMSE','sMAPE']])}

Se elige **{r['ganador']}**, MAE **{r['MAE_seleccion']:.2f}** pedidos por par. El mejor LightGBM es **{r['mejor_ml']}**. El criterio se fijó antes de leer la tabla de prueba.

Black Friday domina varios errores extremos: el 24 de noviembre de 2017 hubo 1.176 pedidos. El modelo seleccionado lo pronosticó desde cuatro orígenes y no disponía de un Black Friday anterior en el período útil. Por ejemplo, desde {peores.iloc[0].origen}, a h={int(peores.iloc[0].h)}, estimó {peores.iloc[0].pred:.2f}, frente a {int(peores.iloc[0].real)} reales. Su RMSE resulta mucho mayor que MAE porque los errores grandes se elevan al cuadrado. No se elimina esa fecha para embellecer el resultado.

### 20.4. Lo que aporta cada factor de LightGBM

{tabla_md(abl[['comparacion','diferencia_MAE','origenes_mejora','origenes']])}

La diferencia es MAE del candidato menos MAE de la referencia: negativo favorece al candidato. Con objetivo absoluto, pasar a variables ampliadas {cambio('Variables con objetivo absoluto')}; con objetivo relativo, {cambio('Variables con objetivo relativo')}. Cambiar al objetivo relativo {cambio('Objetivo con variables básicas')} con variables básicas y {cambio('Objetivo con variables ampliadas')} con ampliadas. {'La hipótesis de que escalar respecto al nivel reciente ayudaría no queda respaldada por este experimento.' if relativo_peor else 'El efecto del objetivo relativo depende de la familia de variables.'}

Un ejemplo muestra que la adaptación relativa puede fallar de forma importante:

{tabla_md(ej_rel)}

Estas son predicciones emitidas el {origen_ej} para el {fecha_ej}. El desacierto relativo es observable; atribuirlo a una sola variable requeriría otra investigación. No se afirma que toda transformación relativa sea inferior en cualquier serie.

### 20.5. Evaluación retrospectiva

{tabla_md(mt[['modelo','MAE','RMSE','sMAPE','sesgo']])}

El elegido obtiene MAE **{r['MAE_prueba']:.2f}**, frente a **{r['MAE_estacional_prueba']:.2f}** de la referencia semanal: una diferencia aproximada de **{mejora:.2f} %**. Es pequeña y no demuestra superioridad general. {lectura_minimo()}

El sesgo del seleccionado es **{sesgo:.2f} pedidos**: en promedio pronosticó por debajo de lo observado. Su MAE posterior supera al de selección; el desempeño no se trasladó de forma uniforme entre períodos. No puede atribuirse la discrepancia exclusivamente a un evento sin evidencia adicional.

Las curvas por horizonte tienen solo cinco emisiones en cada h y no son monótonas por obligación. La tabla de igual peso por fecha y los archivos por origen permiten distinguir el efecto del protocolo de una conclusión sobre todos los días futuros.

### 20.6. Incertidumbre observada y sus límites

Intervalos diarios:

{tabla_md(cd.assign(cobertura_porcentaje=cd.cobertura*100)[['metodo_intervalo','cubiertos','n','cobertura_porcentaje','ancho_medio']])}

Intervalos de totales semanales:

{tabla_md(cs.assign(cobertura_porcentaje=cs.cobertura*100)[['metodo_intervalo','cubiertos','n','cobertura_porcentaje','ancho_medio']])}

El método relativo principal cubre **{principal.cobertura:.2%}** de los pares diarios, por debajo del 90 % nominal. En totales semanales cubre **{principal_s.cobertura:.1%}**. **No alcanza el objetivo de cobertura en esta evaluación.** No debe presentarse como un margen validado al 90 % para decisiones operativas.

El método absoluto muestra {absoluto.cobertura:.2%} diario y {absoluto_s.cobertura:.1%} semanal, con mayor amplitud. Tampoco garantiza cobertura futura. Se conservan ambos resultados y no se elige retrospectivamente el método que mejor lució en prueba.

El margen relativo se reduce cuando la predicción es baja. El sesgo de subpronóstico observado es compatible con parte de la pérdida de cobertura, pero esta explicación no identifica una causa única. Por semana de horizonte, la cobertura diaria relativa más baja es {cds[cds.metodo_intervalo.eq('relativo')].cobertura.min():.2%}; el promedio global oculta diferencias importantes.

En calibración se conservan los días de huelga:

{tabla_md(cal_eventos)}

Son pares solapados y el período comparado difiere del resto. El mayor error en esa ventana describe el episodio; no estima un efecto causal. Incluirlo reconoce riesgos históricos, aunque no basta para garantizar cobertura ante otros regímenes.

### 20.7. Pronóstico final e interpretación

Se reajusta {r['ganador']} y la suma de sus 28 puntos es **{r['total_puntos_28_dias']:,.2f} pedidos**. Se presenta como suma de estimaciones puntuales, sin atribuirle automáticamente el significado de media esperada o mediana del total.

{tabla_md(final[['semana','desde','hasta','pred','inferior','superior']])}

Los rangos son relativos y nominales al 90 %, sujetos al incumplimiento de cobertura observado anteriormente. El período es histórico; no conocemos una cobertura verificada para estas fechas finales dentro del tramo útil. Para una aplicación real, correspondería estudiar nuevos datos y validar una estrategia de calibración antes de tratar estos límites como suficientes.

La importancia por ganancia del mejor LightGBM coloca en sus primeros lugares {', '.join(imp.variable.head(4))}. Esto describe qué divisiones ayudaron al ajuste; no prueba causas del volumen de pedidos.

### 20.8. Resultado de la auditoría

Se completaron **{len(audit['comprobaciones'])} grupos de comprobaciones**, incluidos los ocho modelos con futuro físicamente retirado en dos orígenes. Los tres notebooks tienen ejecución secuencial, comentarios, figuras incorporadas y ningún error de celda. La auditoría respalda la consistencia de cifras y procedimientos, no la suficiencia predictiva para cualquier uso.
'''
base=(D/'guia_completa.md').read_text(encoding='utf-8').split('## 20. Lectura detallada')[0].rstrip()
(D/'guia_completa.md').write_text(base+'\n\n'+lectura+'\n',encoding='utf-8')

secciones=[]
def seccion(titulo,textos=(),tablas=(),figuras=()):
    secciones.append(dict(titulo=titulo,textos=list(textos),tablas=list(tablas),figuras=list(figuras)))
seccion('1. Problema y protocolo',[
 'Pronosticar órdenes recibidas por día durante los siguientes 28 días, desde el cierre de cada domingo: cada emisión cubre cuatro semanas completas de lunes a domingo. Alcance: Módulo 0 y Módulo B. La unidad es la orden; la fecha es la compra. El conteo incluye todos los estados finales.',
 f'Período útil: {r["inicio"]} a {FIN}. La cobertura continua llega a {CORTE}; la serie se corta en el último domingo anterior o igual a esa fecha. El corte responde a cobertura y no demuestra una causa específica para la caída de registros al final. Toda la evaluación es retrospectiva: las fechas de prueba ya eran conocidas.',
 f'Selección: {r["ganador"]}, MAE {r["MAE_seleccion"]:.2f}. Prueba: MAE {r["MAE_prueba"]:.2f}, frente a {r["MAE_estacional_prueba"]:.2f} de la referencia semanal. La cobertura diaria relativa fue {principal.cobertura:.1%}, inferior al 90 % nominal.',
 'Los modelos se reajustan en cada emisión. Los objetivos no se cruzan entre etapas; dentro de cada una se solapan las ventanas. No se considera que todos los pares sean independientes.'
],[(pd.DataFrame([
 ['Selección',*objetivos(SELECCION),len(SELECCION)],['Calibración',*objetivos(CALIBRACION),len(CALIBRACION)],['Prueba',*objetivos(PRUEBA),len(PRUEBA)]],
 columns=['Etapa','Objetivos desde','Objetivos hasta','Emisiones']),'Fechas objetivo del protocolo')],['protocolo_temporal'])
seccion('2. Datos, calidad y cobertura',[
 'Se consulta DuckDB en modo de solo lectura. SQL realiza lecturas, uniones, filtros, agregaciones y ventanas de datos. La serie nace de orders sin multiplicar compras mediante artículos ni pagos.',
 f'El calendario diario completo representa ceros si falta actividad dentro del intervalo. Se obtienen {r["n_dias"]} días y {r["total_pedidos"]:,} órdenes; la auditoría concilia sus valores. Las fechas extremas se inspeccionan antes de definir el universo del ejercicio.',
 f'EDA común: mediana de entrega {entrega.mediana_dias_entrega:.0f} días, p90 {entrega.p90_dias_entrega:.0f} y {entrega.proporcion_tarde:.2%} tardías en las observaciones elegibles. Los compradores con varias compras son {recurrentes:,} de {nclientes:,} identidades únicas. Los atributos finales de entrega no son predictores.',
 f'Geografía del cliente (customer_unique_id): {lectura_geo}'
],[(pd.DataFrame([['Órdenes en la base',99441],['Filas de unión directa ítems y pagos',118434],['Órdenes sin ítems',775],['Órdenes sin pagos',1],['Diferencias monetarias > 2 centavos',280],['Compras sin fecha / IDs duplicados','0 / 0']],columns=['Comprobación','Resultado']),'Calidad relevante al objetivo')],['serie_diaria','segmentos_region'])
seccion('3. Diagnóstico temporal inicial',[
 f'Se estudian solo {sar["n_dias"]} días, hasta {sar["origen"]}. Las medias móviles SQL terminan en la fecha observada. El patrón semanal se resume por medias y medianas; no se interpreta causalmente.',
 'STL robusta con período 7 separa tendencia, semana y residuo para descripción. Sus componentes no se usan como variables porque la descomposición puede utilizar vecinos posteriores dentro del tramo.',
 f'ADF y KPSS parten de hipótesis distintas. Nivel: {lectura_est("nivel")}. Diferencia semanal: {lectura_est("diferencia_7")}. Las pruebas orientan; no determinan un único modelo.'
],[(est[['serie','ADF_p','KPSS_limite']].assign(ADF_p=lambda d:d.ADF_p.map(lambda x:f'{x:.6g}')),'Pruebas de estacionariedad')],['acf_pacf_inicial'])
seccion('4. Variables y prevención de fuga',[
 'Cada ejemplo representa origen o y horizonte h. La historia termina en o, la fecha objetivo es o+h y su calendario sí es conocido. El objetivo real nunca forma parte de las entradas.',
 'Se exige que la fecha de la etiqueta sea menor o igual al origen del ajuste. Filtrar únicamente el origen de la fila permitiría etiquetas todavía desconocidas. Todas las variantes ML comparten filas con 91 días completos de historial.',
 'El modelo ML es directo global: un único modelo aprende todos los horizontes usando h. No utiliza reales intermedios ni una cadena recursiva de predicciones.',
 'Objetivo relativo: log(1+y)-log(1+media28). Inversión: exp(r)*(1+media28)-1, usando la media del origen y recortando a cero. L1 apunta a una mediana condicional; no equivale automáticamente a estimar la media.'
],[(pd.DataFrame([
 ['Básicas','Rezagos 0, 6, 13, 27; medias 7/28; dispersión 28'],['Calendario','Horizonte, semana, mes, tendencia y eventos conocidos'],['Ampliadas','Últimos 7 días, media 91, razones y dispersión relativa'],['Día comparable','Último mismo día de semana y media de cuatro'],['Relativas','Rezagos y días comparables respecto a media 28']
],columns=['Grupo','Contenido']),'Características SQL'),
 (leer('ejemplo_variables')[['h','lag_0','media_28','ultimo_mismo_dia','media_4_mismo_dia']],'Ejemplo desde el primer origen')])
seccion('5. Candidatos y selección',[
 'Ingenuo repite el último valor; Estacional_7 repite la última semana. ETS combina nivel, tendencia amortiguada y semana aditiva. SARIMAX usa log1p, errores ARIMA(1,1,1), seis indicadores semanales y calendario. No tiene diferencia semanal adicional.',
 'Las cuatro variantes LightGBM cruzan variables básicas/ampliadas y objetivo absoluto/relativo con idénticos 300 árboles, 7 hojas y pérdida L1. No se presupone que el relativo sea superior.',
 f'Se elige {r["ganador"]} por MAE en 840 pares. Los días difíciles permanecen. Black Friday 2017 tiene 1.176 pedidos y no había un evento anterior para estimar su magnitud; varios de los mayores errores corresponden a esa fecha.',
 'Los avisos de ajuste se registran; ningún ajuste sin convergencia se acepta. En el primer SARIMAX, Ljung–Box p7=%.4f y p14=%.4f; no demostrar autocorrelación al 5 %% no prueba adecuación universal.'%(sar['Ljung_Box_p7'],sar['Ljung_Box_p14'])
],[(ms[['modelo','MAE','RMSE','sMAPE']],'Selección: menor es mejor'),
 (abl[['comparacion','diferencia_MAE','origenes_mejora']],'Factores ML: diferencia negativa favorece al candidato')])
seccion('6. Variación entre períodos y errores',[
 'Las diferencias por origen importan: un promedio puede ocultar episodios malos. Las emisiones solapadas no se tratan como observaciones independientes para declarar significancia estadística.',
 f'Con objetivo absoluto, pasar a variables ampliadas {cambio("Variables con objetivo absoluto")}; el objetivo relativo {"empeora" if relativo_peor else "no empeora de forma uniforme"} el promedio en esta ejecución. Esa conclusión está limitada a candidatos, configuración y protocolo evaluados.',
 'El calendario informa la fecha de un evento, no su magnitud. Se conserva la huelga y no se proporciona un indicador futuro que simule conocimiento previo. Las comparaciones de eventos son descriptivas.',
 'Ljung–Box y la ACF residual examinan estructura remanente. Un ajuste que converge puede seguir teniendo sesgo o errores predictivos importantes.'
],[],['mae_origen_seleccion','residuos_sarimax'])
seccion('7. Evaluación retrospectiva',[
 'La prueba contiene cinco emisiones, 140 pares por modelo y 56 fechas. Los objetivos centrales se evalúan desde varias anticipaciones. Se exporta también una métrica con igual peso por fecha.',
 f'El elegido logra MAE {r["MAE_prueba"]:.2f}, una diferencia de {mejora:.2f} % frente al estacional. {lectura_minimo(False)}',
 f'El sesgo del seleccionado es {sesgo:.2f} pedidos: subpronóstico promedio. RMSE penaliza picos, sMAPE da una lectura relativa y MAE permanece en pedidos. Los errores por horizonte no tienen por qué crecer de forma monótona.'
],[(mt[['modelo','MAE','RMSE','sMAPE']],'Prueba: comparación en idénticos pares')],['metricas_horizonte_prueba'])
seccion('8. Intervalos y cobertura',[
 'La calibración utiliza 12 emisiones reservadas. Por semana del horizonte hay 84 errores diarios y se toma el rango 77 para 90 %. Para cada total semanal hay 12 errores y el rango es 12. Se usa orden estadístico exacto, sin interpolación.',
 'Relativo: |real-pred|/(1+pred); margen q*(1+pred). Absoluto: |real-pred|; margen q. El relativo es principal por diseño y el absoluto es un análisis paralelo. Los cuantiles permanecen fijos en prueba.',
 'Para totales se suman primero reales y puntos y luego se calibra el error del total. No se suman límites diarios. No hay garantía de cobertura conjunta de todos los días o semanas.',
 f'El relativo cubre {principal.cobertura:.1%} diario y {principal_s.cobertura:.1%} semanal: no alcanza el 90 % nominal. La dependencia, poca muestra y reajustes impiden atribuir una garantía conformal exacta. Las amplitudes y coberturas deben leerse juntas.'
],[(cd.assign(porcentaje=cd.cobertura*100)[['metodo_intervalo','cubiertos','n','porcentaje','ancho_medio']],'Cobertura diaria (%) y amplitud en pedidos'),
 (cs.assign(porcentaje=cs.cobertura*100)[['metodo_intervalo','cubiertos','n','porcentaje','ancho_medio']],'Cobertura de totales semanales (%)')])
seccion('9. Pronóstico histórico final',[
 f'Se reajusta {r["ganador"]} hasta el domingo {FIN} y se pronostica del lunes {final_desde} al domingo {final_hasta}: cuatro semanas completas. Suma de puntos: {r["total_puntos_28_dias"]:,.2f} pedidos. No es una proyección actual de Olist.',
 'Los CSV conservan precisión decimal. La suma de puntos no se presenta como media esperada ni mediana garantizada del total. Los reales futuros permanecen desconocidos.',
 'Los intervalos finales son los relativos fijados en el protocolo; su cobertura observada fue insuficiente en prueba. No se presentan como márgenes operativamente validados al 90 %. No se anuncia un intervalo mensual sumando los semanales.'
],[(final[['semana','desde','hasta','pred','inferior','superior']],'Totales semanales con intervalos nominales')],['pronostico_final'])
seccion('10. Reproducibilidad, auditoría y límites',[
 'Entorno: Python 3.12, dependencias directas fijadas en requirements.txt. La base local se construye con el script del curso. El análisis usa SQL y read_only=True; la base no se incluye en la entrega.',
 'Orden: instalar requisitos; construir data/olist.duckdb; ejecutar scripts/ejecutar.py; scripts/auditar.py; scripts/generar_documentacion.py. Los notebooks ya se entregan ejecutados, con figuras incrustadas y comentarios.',
 f'La auditoría completa {len(audit["comprobaciones"])} grupos de controles: serie, particiones, métricas independientes, baselines, variables, cuantiles, cobertura y reproducibilidad final. Los ocho modelos reproducen sus pronósticos al retirar físicamente el futuro en dos orígenes.',
 'Límites: período corto, una sola observación útil de Black Friday, dependencia entre emisiones, elección de cobertura temporal y prueba ya examinada. La diferencia de MAE frente al baseline es pequeña y la cobertura principal no alcanza el nivel nominal.',
 'Material didáctico: documentacion/guia_completa.md desarrolla cada concepto y analiza todas las tablas. La importancia por ganancia de ML explica el ajuste sin atribuir causalidad.',
 'Datos: Brazilian E-Commerce Public Dataset by Olist (Kaggle). Revisar licencia CC BY-NC-SA 4.0 antes de redistribuir datos derivados. Referencias metodológicas: Forecasting: Principles and Practice; documentación de statsmodels, LightGBM y holidays.'
],[(pd.DataFrame([['SQL y datos','Conteos, regularidad, granularidad y ventanas'],['Evaluación','Métricas SQL y referencias reproducidas'],['Fuga','Futuro retirado, 8 modelos, 2 orígenes'],['Intervalos','Cuantiles y totales conciliados'],['Notebooks','Tres ejecutados, sin errores y comentados']],columns=['Área','Evidencia']),'Controles auditados')])

# Markdown consolidado; referencias relativas renderizables en GitHub.
md=['# Pronóstico diario de órdenes de Olist','',
    'Módulos 0 y B · horizonte 28 días · evaluación semanal retrospectiva','']
for s in secciones:
    md+=['## '+s['titulo'],'']
    for t in s['textos']:md += [t,'']
    for df,caption in s['tablas']:md += ['**'+caption+'**','',tabla_md(df),'']
    for fig in s['figuras']:md += [f'![{fig.replace("_"," ")}](figuras/{fig}.png)','']
(D/'informe.md').write_text('\n'.join(md),encoding='utf-8')

# PDF con tipografía Unicode y tablas ajustadas al ancho de la página.
fontdir=Path('/usr/share/fonts/truetype/dejavu')
if (fontdir/'DejaVuSans.ttf').exists():
    pdfmetrics.registerFont(TTFont('Lectura',str(fontdir/'DejaVuSans.ttf')))
    pdfmetrics.registerFont(TTFont('LecturaBold',str(fontdir/'DejaVuSans-Bold.ttf')))
else:
    # ReportLab distribuye Vera, evitando una dependencia de fuentes del sistema.
    import reportlab
    fonts=Path(reportlab.__file__).parent/'fonts'
    pdfmetrics.registerFont(TTFont('Lectura',str(fonts/'Vera.ttf')))
    pdfmetrics.registerFont(TTFont('LecturaBold',str(fonts/'VeraBd.ttf')))
styles=getSampleStyleSheet()
styles.add(ParagraphStyle(name='TextoOlist',fontName='Lectura',fontSize=9.3,leading=13,spaceAfter=9))
styles.add(ParagraphStyle(name='TituloOlist',fontName='LecturaBold',fontSize=16,leading=20,spaceAfter=14,textColor=colors.HexColor('#17324D')))
styles.add(ParagraphStyle(name='TablaOlist',fontName='Lectura',fontSize=7.1,leading=9))
styles.add(ParagraphStyle(name='CabeceraOlist',fontName='LecturaBold',fontSize=7.2,leading=9,textColor=colors.white))
styles.add(ParagraphStyle(name='PieOlist',fontName='LecturaBold',fontSize=9,leading=12,spaceBefore=6,spaceAfter=6))
W=17.4*cm
story=[]
def par(t,style='TextoOlist'):return Paragraph(escape(str(t)),styles[style])
for i,s in enumerate(secciones):
    if i:story.append(PageBreak())
    story.append(par(s['titulo'],'TituloOlist'))
    for t in s['textos']:story.append(par(t))
    for df,caption in s['tablas']:
        story.append(par(caption,'PieOlist'))
        rows=[[par(c,'CabeceraOlist') for c in df.columns]]
        rows += [[par(fmt(v),'TablaOlist') for v in fila] for fila in df.itertuples(index=False,name=None)]
        # El nombre de modelo necesita más espacio que una métrica numérica.
        n=len(df.columns)
        if n==2:widths=[W*.32,W*.68]
        elif str(df.columns[0]) in ('modelo','comparacion'):widths=[W*.40]+[W*.60/(n-1)]*(n-1)
        else:widths=[W/n]*n
        t=Table(rows,colWidths=widths,repeatRows=1,hAlign='LEFT')
        t.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),colors.HexColor('#17324D')),
            ('ROWBACKGROUNDS',(0,1),(-1,-1),[colors.HexColor('#F1F5F9'),colors.white]),
            ('VALIGN',(0,0),(-1,-1),'TOP'),('LEFTPADDING',(0,0),(-1,-1),5),
            ('RIGHTPADDING',(0,0),(-1,-1),5),('TOPPADDING',(0,0),(-1,-1),5),
            ('BOTTOMPADDING',(0,0),(-1,-1),5),('LINEBELOW',(0,0),(-1,0),.6,colors.white)]))
        story += [t,Spacer(1,9)]
    for fig in s['figuras']:
        im=Image(str(D/'figuras'/f'{fig}.png'))
        h=W*im.imageHeight/im.imageWidth
        maxh=7.0*cm if len(s['figuras'])>1 else 7.7*cm
        scale=min(1,maxh/h)
        im.drawWidth=W*scale;im.drawHeight=h*scale
        story += [im,Spacer(1,7)]

def pie(canvas,doc):
    canvas.setFont('Lectura',7)
    canvas.setFillColor(colors.HexColor('#526273'))
    canvas.drawString(1.8*cm,1.1*cm,'Olist · Series de tiempo · Evaluación retrospectiva')
    canvas.drawRightString(19.2*cm,1.1*cm,str(doc.page))
    canvas.setTitle('Olist: pronóstico diario a 28 días')
    canvas.setAuthor('Solución del taller de series de tiempo')
doc=SimpleDocTemplate(str(D/'informe.pdf'),pagesize=(21*cm,29.7*cm),
    rightMargin=1.8*cm,leftMargin=1.8*cm,topMargin=1.6*cm,bottomMargin=1.8*cm)
doc.build(story,onFirstPage=pie,onLaterPages=pie)

readme=f'''# Olist: pronóstico de pedidos a 28 días

Solución autónoma de los **Módulos 0 y B** del taller de Aprendizaje Automático. Incluye preparación y calidad de datos, exploración temporal, modelos estadísticos y de ML, evaluación semanal, intervalos y auditoría. Los notebooks están ejecutados y comentados en español.

## Ruta de lectura

1. **[Guía completa](documentacion/guia_completa.md):** explica desde cero el problema, cada desarrollo y la interpretación concreta de resultados.
2. [Datos y calidad](notebooks/00_datos_y_calidad.ipynb).
3. [Exploración temporal](notebooks/01_exploracion_temporal.ipynb): incluye una tabla visible de festivos y eventos especiales.
4. [Modelado y pronóstico](notebooks/02_modelado_y_pronostico.ipynb).
5. [Informe PDF](documentacion/informe.pdf), [informe Markdown](documentacion/informe.md) y [auditoría](documentacion/auditoria.md).

## Resultados y lectura correcta

- Serie: **{r['n_dias']} días**, {r['total_pedidos']:,} compras, de {r['inicio']} a {r['fin']}.
- Protocolo: {len(SELECCION)} emisiones de selección, {len(CALIBRACION)} de calibración y {len(PRUEBA)} de prueba. Cada emisión parte de un domingo y cubre 28 días (cuatro semanas lunes–domingo); los orígenes avanzan semanalmente.
- Seleccionado: **{r['ganador']}**, MAE {r['MAE_seleccion']:.2f} en selección y {r['MAE_prueba']:.2f} en prueba. Referencia semanal: {r['MAE_estacional_prueba']:.2f} en prueba. {lectura_minimo(False)}
- El objetivo relativo de LightGBM {'no mejora' if relativo_peor else 'no mejora de forma uniforme'} el promedio en este experimento. La comparación controlada queda documentada con sus resultados.
- **Los intervalos relativos no alcanzan el 90 % nominal:** cobertura diaria {principal.cobertura:.2%} ({int(principal.cubiertos)}/{int(principal.n)}) y semanal {principal_s.cobertura:.1%} ({int(principal_s.cubiertos)}/{int(principal_s.n)}). No se presentan como márgenes operativamente validados al 90 %.
- Pronóstico histórico del lunes {final_desde} al domingo {final_hasta}: **{r['total_puntos_28_dias']:,.2f}** como suma de puntos. No equivale automáticamente a media esperada o mediana del total.
- **Evaluación retrospectiva:** las fechas de prueba ya eran conocidas. No es una nueva prueba ciega ni una proyección actual de Olist.

## Reproducir

Entorno utilizado: Python 3.12; versiones directas fijadas en `requirements.txt` y entorno registrado en `resultados/entorno.json`.

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

`crear_notebooks.py` contiene su fuente editorial; regenerarlos elimina sus salidas. Solo se necesita al mantener el material: después hay que ejecutar nuevamente los notebooks y la auditoría.

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

- `metricas_seleccion.csv`, `metricas_prueba.csv`: comparación global de ocho candidatos.
- `comparacion_componentes.csv`: efecto de variables y objetivo de LightGBM.
- `metricas_horizonte_*`, `metricas_origen_*`, `metricas_semana_*`: detalle temporal.
- `metricas_prueba_igual_peso_fecha.csv`: sensibilidad al peso de fechas solapadas.
- `cuantiles_intervalos.csv` y `cobertura_*`: calibración, amplitud y cobertura verificables.
- `pronostico_diario_28_dias.csv` y `pronostico_semanal.csv`: puntos y límites finales; no se suman límites diarios para construir los semanales.
- `auditoria.json`, `entorno.json`, `huellas_csv.json`: evidencia de verificación y reproducción.

## Alcance y atribución

No incluye módulos A, C o D ni la extensión opcional por categoría/estado. El script de construcción suministrado en el curso se conserva. Datos: [Brazilian E-Commerce Public Dataset by Olist](https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce), versión 2 utilizada en esta ejecución. Revisar la licencia **CC BY-NC-SA 4.0** antes de redistribuir datos derivados.

La entrega excluye `data/olist.duckdb`, entornos virtuales y cachés. Está preparada para un repositorio; no se ha publicado en GitHub.
'''
(ROOT/'README.md').write_text(readme.replace('\n documentacion/','\ndocumentacion/'),encoding='utf-8')
print('Documentación generada: guía con resultados, informe Markdown/PDF y README.')
