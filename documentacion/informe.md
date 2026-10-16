# Pronóstico diario de órdenes de Olist

Módulos 0 y B · horizonte 28 días · evaluación semanal retrospectiva

## 1. Problema y protocolo

Pronosticar órdenes recibidas por día durante los siguientes 28 días, desde el cierre de cada martes. Alcance: Módulo 0 y Módulo B. La unidad es la orden; la fecha es la compra. El conteo incluye todos los estados finales.

Período útil: 2017-02-01 a 2018-08-21. El corte responde a cobertura y no demuestra una causa específica para la caída de registros al final. Toda la evaluación es retrospectiva: las fechas de prueba ya eran conocidas.

Selección: SARIMAX_calendario, MAE 43.11. Prueba: MAE 65.82, frente a 67.02 de la referencia semanal. La cobertura diaria relativa fue 76.4%, inferior al 90 % nominal.

Los modelos se reajustan en cada emisión. Los objetivos no se cruzan entre etapas; dentro de cada una se solapan las ventanas. No se considera que todos los pares sean independientes.

**Fechas objetivo del protocolo**

| Etapa | Objetivos desde | Objetivos hasta | Emisiones |
| --- | --- | --- | --- |
| Selección | 2017-07-26 | 2018-03-13 | 30 |
| Calibración | 2018-03-14 | 2018-06-26 | 12 |
| Prueba | 2018-06-27 | 2018-08-21 | 5 |

![protocolo temporal](figuras/protocolo_temporal.png)

## 2. Datos, calidad y cobertura

Se consulta DuckDB en modo de solo lectura. SQL realiza lecturas, uniones, filtros, agregaciones y ventanas de datos. La serie nace de orders sin multiplicar compras mediante artículos ni pagos.

El calendario diario completo representa ceros si falta actividad dentro del intervalo. Se obtienen 567 días y 97.590 órdenes; la auditoría concilia sus valores. Las fechas extremas se inspeccionan antes de definir el universo del ejercicio.

EDA común: mediana de entrega 10 días, p90 23 y 6.77% tardías en las observaciones elegibles. Los compradores con varias compras son 2,997 de 96,096 identidades únicas. Los atributos finales de entrega no son predictores.

**Calidad relevante al objetivo**

| Comprobación | Resultado |
| --- | --- |
| Órdenes en la base | 99441 |
| Filas de unión directa ítems y pagos | 118434 |
| Órdenes sin ítems | 775 |
| Órdenes sin pagos | 1 |
| Diferencias monetarias > 2 centavos | 280 |
| Compras sin fecha / IDs duplicados | 0 / 0 |

![serie diaria](figuras/serie_diaria.png)

## 3. Diagnóstico temporal inicial

Se estudian solo 175 días, hasta 2017-07-25. Las medias móviles SQL terminan en la fecha observada. El patrón semanal se resume por medias y medianas; no se interpreta causalmente.

STL robusta con período 7 separa tendencia, semana y residuo para descripción. Sus componentes no se usan como variables porque la descomposición puede utilizar vecinos posteriores dentro del tramo.

ADF y KPSS parten de hipótesis distintas. Nivel: ADF no rechaza raíz unitaria y KPSS rechaza estacionariedad. Diferencia semanal: ADF rechaza y KPSS no rechaza. Las pruebas orientan; no determinan un único modelo.

**Pruebas de estacionariedad**

| serie | ADF_p | KPSS_limite |
| --- | --- | --- |
| nivel | 0.710938 | <= 0.01 |
| diferencia_1 | 4.71204e-06 | 0.0417 |
| diferencia_7 | 0.00176203 | >= 0.10 |

![acf pacf inicial](figuras/acf_pacf_inicial.png)

## 4. Variables y prevención de fuga

Cada ejemplo representa origen o y horizonte h. La historia termina en o, la fecha objetivo es o+h y su calendario sí es conocido. El objetivo real nunca forma parte de las entradas.

Se exige que la fecha de la etiqueta sea menor o igual al origen del ajuste. Filtrar únicamente el origen de la fila permitiría etiquetas todavía desconocidas. Todas las variantes ML comparten filas con 91 días completos de historial.

El modelo ML es directo global: un único modelo aprende todos los horizontes usando h. No utiliza reales intermedios ni una cadena recursiva de predicciones.

Objetivo relativo: log(1+y)-log(1+media28). Inversión: exp(r)*(1+media28)-1, usando la media del origen y recortando a cero. L1 apunta a una mediana condicional; no equivale automáticamente a estimar la media.

**Características SQL**

| Grupo | Contenido |
| --- | --- |
| Básicas | Rezagos 0, 6, 13, 27; medias 7/28; dispersión 28 |
| Calendario | Horizonte, semana, mes, tendencia y eventos conocidos |
| Ampliadas | Últimos 7 días, media 91, razones y dispersión relativa |
| Día comparable | Último mismo día de semana y media de cuatro |
| Relativas | Rezagos y días comparables respecto a media 28 |

**Ejemplo desde el primer origen**

| h | lag_0 | media_28 | ultimo_mismo_dia | media_4_mismo_dia |
| --- | --- | --- | --- | --- |
| 1 | 153 | 128.39 | 153 | 142.75 |
| 7 | 153 | 128.39 | 153 | 158.75 |
| 28 | 153 | 128.39 | 153 | 158.75 |

## 5. Candidatos y selección

Ingenuo repite el último valor; Estacional_7 repite la última semana. ETS combina nivel, tendencia amortiguada y semana aditiva. SARIMAX usa log1p, errores ARIMA(1,1,1), seis indicadores semanales y calendario. No tiene diferencia semanal adicional.

Las cuatro variantes LightGBM cruzan variables básicas/ampliadas y objetivo absoluto/relativo con idénticos 300 árboles, 7 hojas y pérdida L1. No se presupone que el relativo sea superior.

Se elige SARIMAX_calendario por MAE en 840 pares. Los días difíciles permanecen. Black Friday 2017 tiene 1.176 pedidos y no había un evento anterior para estimar su magnitud; varios de los mayores errores corresponden a esa fecha.

Los avisos de ajuste se registran; ningún ajuste sin convergencia se acepta. En el primer SARIMAX, Ljung–Box p7=0.0539 y p14=0.2208; no demostrar autocorrelación al 5 % no prueba adecuación universal.

**Selección: menor es mejor**

| modelo | MAE | RMSE | sMAPE |
| --- | --- | --- | --- |
| SARIMAX_calendario | 43.11 | 92.22 | 20.58 |
| LGBM_amplio_absoluto | 51.15 | 102.38 | 23.59 |
| LGBM_base_absoluto | 51.61 | 103.38 | 23.67 |
| ETS_amortiguado | 53.64 | 104.96 | 24.78 |
| Estacional_7 | 56.64 | 122.94 | 25.74 |
| Ingenuo | 58.82 | 101.80 | 27.86 |
| LGBM_amplio_relativo | 64.34 | 132.02 | 26.66 |
| LGBM_base_relativo | 66.56 | 139.19 | 26.90 |

**Factores ML: diferencia negativa favorece al candidato**

| comparacion | diferencia_MAE | origenes_mejora |
| --- | --- | --- |
| Variables con objetivo absoluto | -0.46 | 13 |
| Variables con objetivo relativo | -2.23 | 17 |
| Objetivo con variables básicas | 14.96 | 12 |
| Objetivo con variables ampliadas | 13.19 | 13 |

## 6. Variación entre períodos y errores

Las diferencias por origen importan: un promedio puede ocultar episodios malos. Las emisiones solapadas no se tratan como observaciones independientes para declarar significancia estadística.

Las variables ampliadas ayudan modestamente al ML absoluto, pero el objetivo relativo empeora el promedio en esta ejecución. Esa conclusión está limitada a candidatos, configuración y protocolo evaluados.

El calendario informa la fecha de un evento, no su magnitud. Se conserva la huelga y no se proporciona un indicador futuro que simule conocimiento previo. Las comparaciones de eventos son descriptivas.

Ljung–Box y la ACF residual examinan estructura remanente. Un ajuste que converge puede seguir teniendo sesgo o errores predictivos importantes.

![mae origen seleccion](figuras/mae_origen_seleccion.png)

![residuos sarimax](figuras/residuos_sarimax.png)

## 7. Evaluación retrospectiva

La prueba contiene cinco emisiones, 140 pares por modelo y 56 fechas. Los objetivos centrales se evalúan desde varias anticipaciones. Se exporta también una métrica con igual peso por fecha.

El elegido logra MAE 65.82, una diferencia de 1.79 % frente al estacional. El menor MAE observado pertenece a ETS_amortiguado (65.08); se mantiene la elección de selección.

El sesgo del seleccionado es -43.36 pedidos: subpronóstico promedio. RMSE penaliza picos, sMAPE da una lectura relativa y MAE permanece en pedidos. Los errores por horizonte no tienen por qué crecer de forma monótona.

**Prueba: comparación en idénticos pares**

| modelo | MAE | RMSE | sMAPE |
| --- | --- | --- | --- |
| ETS_amortiguado | 65.08 | 80.50 | 31.01 |
| SARIMAX_calendario | 65.82 | 81.29 | 31.26 |
| LGBM_base_absoluto | 67.01 | 82.35 | 31.61 |
| Estacional_7 | 67.02 | 84.60 | 32.40 |
| LGBM_amplio_absoluto | 67.32 | 83.09 | 31.93 |
| Ingenuo | 68.22 | 84.07 | 31.49 |
| LGBM_base_relativo | 69.31 | 86.53 | 33.12 |
| LGBM_amplio_relativo | 70.43 | 86.43 | 33.43 |

![metricas horizonte prueba](figuras/metricas_horizonte_prueba.png)

## 8. Intervalos y cobertura

La calibración utiliza 12 emisiones reservadas. Por semana del horizonte hay 84 errores diarios y se toma el rango 77 para 90 %. Para cada total semanal hay 12 errores y el rango es 12. Se usa orden estadístico exacto, sin interpolación.

Relativo: |real-pred|/(1+pred); margen q*(1+pred). Absoluto: |real-pred|; margen q. El relativo es principal por diseño y el absoluto es un análisis paralelo. Los cuantiles permanecen fijos en prueba.

Para totales se suman primero reales y puntos y luego se calibra el error del total. No se suman límites diarios. No hay garantía de cobertura conjunta de todos los días o semanas.

El relativo cubre 76.4% diario y 80.0% semanal: no alcanza el 90 % nominal. La dependencia, poca muestra y reajustes impiden atribuir una garantía conformal exacta. Las amplitudes y coberturas deben leerse juntas.

**Cobertura diaria (%) y amplitud en pedidos**

| metodo_intervalo | cubiertos | n | porcentaje | ancho_medio |
| --- | --- | --- | --- | --- |
| absoluto | 123 | 140 | 87.86 | 230.59 |
| relativo | 107 | 140 | 76.43 | 202.46 |

**Cobertura de totales semanales (%)**

| metodo_intervalo | cubiertos | n | porcentaje | ancho_medio |
| --- | --- | --- | --- | --- |
| absoluto | 19 | 20 | 95.00 | 1,812.88 |
| relativo | 16 | 20 | 80.00 | 1,578.66 |

## 9. Pronóstico histórico final

Se reajusta SARIMAX_calendario hasta 2018-08-21 y se pronostica 2018-08-22 a 2018-09-18. Suma de puntos: 6,460.58 pedidos. No es una proyección actual de Olist.

Los CSV conservan precisión decimal. La suma de puntos no se presenta como media esperada ni mediana garantizada del total. Los reales futuros permanecen desconocidos.

Los intervalos finales son los relativos fijados en el protocolo; su cobertura observada fue insuficiente en prueba. No se presentan como márgenes operativamente validados al 90 %. No se anuncia un intervalo mensual sumando los semanales.

**Totales semanales con intervalos nominales**

| semana | desde | hasta | pred | inferior | superior |
| --- | --- | --- | --- | --- | --- |
| 1 | 2018-08-22 | 2018-08-28 | 1,619.98 | 972.03 | 2,267.92 |
| 2 | 2018-08-29 | 2018-09-04 | 1,625.55 | 454.05 | 2,797.05 |
| 3 | 2018-09-05 | 2018-09-11 | 1,589.51 | 623.55 | 2,555.47 |
| 4 | 2018-09-12 | 2018-09-18 | 1,625.55 | 614.30 | 2,636.80 |

![pronostico final](figuras/pronostico_final.png)

## 10. Reproducibilidad, auditoría y límites

Entorno: Python 3.12, dependencias directas fijadas en requirements.txt. La base local se construye con el script del curso. El análisis usa SQL y read_only=True; la base no se incluye en la entrega.

Orden: instalar requisitos; construir data/olist.duckdb; ejecutar scripts/ejecutar.py; scripts/auditar.py; scripts/generar_documentacion.py. Los notebooks ya se entregan ejecutados, con figuras incrustadas y comentarios.

La auditoría completa 12 grupos de controles: serie, particiones, métricas independientes, baselines, variables, cuantiles, cobertura y reproducibilidad final. Los ocho modelos reproducen sus pronósticos al retirar físicamente el futuro en dos orígenes.

Límites: período corto, una sola observación útil de Black Friday, dependencia entre emisiones, elección de cobertura temporal y prueba ya examinada. La diferencia de MAE frente al baseline es pequeña y la cobertura principal no alcanza el nivel nominal.

Material didáctico: documentacion/guia_completa.md desarrolla cada concepto y analiza todas las tablas. La importancia por ganancia de ML explica el ajuste sin atribuir causalidad.

Datos: Brazilian E-Commerce Public Dataset by Olist (Kaggle). Revisar licencia CC BY-NC-SA 4.0 antes de redistribuir datos derivados. Referencias metodológicas: Forecasting: Principles and Practice; documentación de statsmodels, LightGBM y holidays.

**Controles auditados**

| Área | Evidencia |
| --- | --- |
| SQL y datos | Conteos, regularidad, granularidad y ventanas |
| Evaluación | Métricas SQL y referencias reproducidas |
| Fuga | Futuro retirado, 8 modelos, 2 orígenes |
| Intervalos | Cuantiles y totales conciliados |
| Notebooks | Tres ejecutados, sin errores y comentados |
