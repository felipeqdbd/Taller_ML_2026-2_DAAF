# Capítulo B — Series de tiempo: demanda diaria de órdenes

> **Borrador para el informe final.** Las cifras salen de `notebooks/B_series.ipynb` (ejecución completa, semilla 42) y las figuras están en `informe/figuras/`. Al final hay una bitácora con todas las decisiones de diseño y su sustento, que puede ir como anexo.

---

## Para el resumen ejecutivo (pregunta 2)

**¿Cuántas órdenes recibirá Olist cada día durante las próximas 4 semanas?** Para las cuatro semanas siguientes al cierre de los datos (20-ago a 16-sep-2018), el modelo seleccionado (SARIMAX con estacionalidad semanal determinística y efectos de calendario) proyecta unas **1 800 órdenes por semana** (≈ 255/día). El patrón semanal es marcado: ~295 órdenes los lunes y ~200 los sábados. El intervalo del 80 % va de ~1 450 a ~2 250 órdenes por semana. En validación con origen móvil, el modelo redujo el error en 23 % frente a "repetir la semana pasada" (MAE de 29 órdenes/día). En las 8 semanas de prueba la ventaja se redujo a 7 %, porque la demanda de agosto-2018 saltó un 38 % sin que la historia diera señales previas. Recomendamos reajustar cada domingo y monitorear el sesgo semanal.

---

## B.1 Formulación

* **Objetivo:** pronosticar el número de órdenes por día (según `order_purchase_timestamp`) para h = 1…28 días después de cada fecha de origen.
* **Uso:** plan semanal de capacidad (atención al cliente, coordinación con vendedores y transportadores). El plan se hace cada domingo para las 4 semanas siguientes, de lunes a domingo.
* **Unidad:** día calendario; se cuentan todas las órdenes, sin importar su estado final.

## B.2 Datos y construcción de la serie (SQL)

Toda la lectura se hace con tres consultas parametrizadas sobre `olist.duckdb`, abierta en modo `read_only=True`:

| Archivo | Contenido | Parámetros |
|---|---|---|
| `sql/B_01_serie_diaria.sql` | Grilla de días (`generate_series`) + `LEFT JOIN` con los conteos por día → los días sin órdenes quedan en 0 | `fecha_inicio`, `fecha_fin`, `estado` (NULL = Brasil) |
| `sql/B_02_calendario.sql` | Día de la semana, feriados nacionales de Brasil, Black Friday, días post-BF, fiestas de fin de año, paro de camioneros, partidos de Brasil en el Mundial | `fecha_inicio`, `fecha_fin` |
| `sql/B_03_features_ml.sql` | Tabla (origen × horizonte) para el modelo de ML: rezagos, medias móviles y variables de calendario, calculados con funciones de ventana | se lee de tablas `TEMP` en memoria creadas a partir de B_01/B_02 |

**Controles de calidad.** La serie tiene 596 días y 97 891 órdenes, y el total cuadra exactamente con un `COUNT(*)` directo sobre `orders`: el `JOIN` con `customers` (relación 1:1 por `customer_id`) no duplica filas. Solo hay 4 días en cero (1 a 4-ene-2017).

**Período útil: 2017-01-01 a 2018-08-19** (figura `B_00_serie_cruda.png`).

* *Inicio:* 2016 tiene unas 330 órdenes repartidas en 15 de 119 días, con noviembre completo en cero; es una fase piloto. Empezar en 2017 también coincide con el Módulo A.
* *Fin:* desde el 22-ago-2018 los conteos caen de ~290 a menos de 20 diarios. Es un **artefacto del corte del extracto**, no demanda real. Se termina el domingo 19-ago para que la prueba tenga 8 semanas completas de lunes a domingo.
* *Ventana de ajuste desde 2017-02-01:* enero de 2017 es el arranque de la plataforma (5–35 órdenes/día). En escala logarítmica esos valores producen saltos que inflarían la varianza estimada. Enero solo se usa como historia para las ventanas del modelo de ML.

> ⚠️ **Coordinar con el Módulo 0:** si el grupo define otro período útil, basta con cambiar `FECHA_INICIO`/`FECHA_FIN` en la celda de configuración del notebook.

## B.3 Análisis de la serie

**Tendencia** (figura `B_01_serie.png`). La demanda pasa de ~64 órdenes/día en feb-2017 a ~150 en oct-2017 y se estabiliza en ~230 desde ene-2018. Luego baja a ~205 en jun–jul-2018 y sube a ~280 en agosto. La fuerza de la tendencia según STL es **0.88**.

**Estacionalidad semanal** (figura `B_02_perfil_semanal.png`). Razón de cada día frente a la media centrada de 7 días, sin días atípicos:

| lun | mar | mié | jue | vie | sáb | dom |
|---|---|---|---|---|---|---|
| 1.17 | 1.13 | 1.10 | 1.05 | 0.95 | 0.77 | 0.86 |

Las desviaciones estándar están entre 0.09 y 0.16. El patrón es estable, lo que anticipa que una estacionalidad **determinística** puede bastar. La fuerza estacional según STL es 0.46.

**Descomposición** (figura `B_03_stl.png`): STL robusta con periodo 7 sobre `log(1+y)`. Se usa el logaritmo porque la amplitud semanal crece con el nivel; en log el patrón pasa de multiplicativo a aditivo.

**Estacionariedad** (ADF: H0 = raíz unitaria; KPSS: H0 = estacionaria):

| Serie | ADF (p) | KPSS (p) | Conclusión |
|---|---|---|---|
| log(1+y) | −2.40 (0.140) | 2.78 (≤0.01) | no estacionaria |
| Δ log(1+y) | −7.64 (<0.001) | 0.13 (≥0.10) | estacionaria |
| Δ Δ7 log(1+y) | −9.78 (<0.001) | 0.02 (≥0.10) | estacionaria |

Con una diferencia regular basta (d = 1).

**ACF/PACF** (figura `B_04_acf_pacf.png`). En nivel, la ACF decae lento y tiene picos en los múltiplos de 7. Después de Δ Δ7 quedan picos negativos en los rezagos 1 y 7, la firma de un MA(1)×MA(1)₇. Esto orientó la grilla del SARIMA.

## B.4 Eventos atípicos

Se compara lo observado con lo esperado, definido como la mediana del mismo día de la semana en las 4 semanas previas (figura `B_05_eventos.png`):

| Evento | Días | Obs./esperado | Tratamiento | Por qué |
|---|---|---|---|---|
| Black Friday 2017 | 1 | ×7.6 | **Modelar** (dummy) | Recurrente y con fecha conocida; el plan de nov-2018 debe anticiparlo |
| Post-BF (sáb–mar) | 4 | ×2.6 | **Modelar** (dummy) | Efecto de arrastre y Cyber Monday, también recurrente |
| Feriados nacionales | 18 | ×0.74 | **Modelar** (dummy) | Fechas conocidas con anticipación |
| Fiestas 24-dic a 1-ene | 9 | ×0.51 | **Modelar** (dummy) | Recurrente; un efecto distinto al de un feriado aislado |
| Paro de camioneros (21–31 may 2018) | 11 | ×0.51 | **Marcar**: dummy en el ajuste, 0 al pronosticar y excluido de las métricas de validación | No es recurrente ni previsible; la dummy evita que sesgue los parámetros |
| Partidos de Brasil, Mundial 2018 | 5 | ×0.85 | **Solo diagnóstico** | Solo 2 partidos antes de la prueba (no alcanza para estimar el efecto) y las fechas de eliminatorias no se conocían al pronosticar |
| Arranque ene-2017 / truncamiento ago-2018 | — | — | **Excluir** | Artefactos de los datos, no demanda |

Los coeficientes del SARIMAX final confirman los efectos, interpretados como cambio multiplicativo `exp(β) − 1`: feriado **−18 %**, Black Friday **×4.5**, post-BF **+73 %**, fiestas **−44 %** y paro **−32 %**. Todos tienen p < 0.001.

## B.5 Partición y validación

* **Prueba:** últimas 8 semanas del período útil, **25-jun a 19-ago-2018** (56 días). Hay 5 orígenes (los domingos del 24-jun al 22-jul) y cada uno pronostica 28 días sin salirse de la prueba. En cada origen se reajusta el modelo con los datos reales hasta ese domingo, como se haría en producción. Órdenes e hiperparámetros quedan fijos desde la validación.
* **Validación walk-forward:** 21 orígenes semanales (7-ene a 27-may-2018), horizonte de 28 días y ventana de ajuste expansiva desde 2017-02-01. El último origen pronostica hasta el 24-jun, así que la prueba no se toca (figura `B_06_particion.png`).
* Los orígenes empiezan en enero de 2018 para que cada ajuste incluya ya un Black Friday y una temporada de fin de año.
* **Criterio de selección:** MAE de validación sin los días del paro. También se reportan RMSE, MAPE, sMAPE y la desviación del MAE entre orígenes.

## B.6 Modelos

**Baselines.** *Ingenuo*: ŷ(o+h) = y(o). *Ingenuo estacional*: ŷ(o+h) = y(o+h−7⌈h/7⌉), es decir, se repite la última semana observada.

**Modelo estadístico: SARIMAX sobre log(1+y).**

* Escala log: estabiliza la varianza y garantiza pronósticos positivos. Los intervalos se transforman con `expm1`, que es monótona. El pronóstico puntual equivale a la mediana, que es lo óptimo para el MAE.
* Se compararon dos familias para la estacionalidad semanal. Dentro de cada una el orden se eligió por AIC con datos hasta el 7-ene-2018; entre familias se eligió por walk-forward, porque el AIC no es comparable con distinto orden de diferenciación:

| Familia | Mejor orden (AIC) | Observación | MAE val. |
|---|---|---|---|
| E: estocástica, (p,1,q)(0,1,1)₇ + eventos | (1,1,2)(0,1,1)₇, AIC −182.2 | **MA estacional = −1.00 (no invertible)** y MA regular = (1−B)(1−0.46B) | 34.1 |
| D: determinística, (p,1,q) + 6 dummies de día + eventos | (1,1,1), AIC −205.3 | MA = −0.75, invertible | **29.0** |
| SARIMA puro (familia E sin exógenas) | (1,1,2)(0,1,1)₇ | referencia para medir el aporte de las exógenas | 34.9 |

  Un MA estacional igual a −1 indica que la diferencia Δ7 sobra: el patrón semanal es determinístico. Por eso se eligió la **familia D**. Sus residuos no muestran autocorrelación (Ljung-Box, p = 0.59, 0.79, 0.33 y 0.12 en los rezagos 7, 14, 21 y 28; figura `B_07_diagnostico_sarimax.png`). El pronóstico multi-paso es recursivo, nativo del filtro de Kalman.

**Modelo de ML: LightGBM con estrategia directa.**

* Se entrena un único modelo con el horizonte como variable, sobre filas (origen, h). Todas las variables se calculan en SQL con ventanas `ROWS … PRECEDING AND CURRENT ROW` sobre la fecha de origen. De la fecha objetivo solo se usan variables de calendario, conocidas de antemano.
* **Directa en vez de recursiva:** no acumula el error de sus propias predicciones durante 28 pasos, y toda la tabla queda en SQL, como pide el taller. Con la estrategia recursiva habría que recalcular los rezagos en Python dentro del bucle.
* **Objetivo relativo:** `log(1+y_{o+h}) − log(1+media28_o)`, con los rezagos expresados igual. Los árboles no extrapolan niveles; así el modelo aprende la forma de la serie y el nivel lo aporta la media de 28 días.
* **Variables:** horizonte, calendario de la fecha objetivo, rezagos relativos 0–6, momentum (media 7 / media 28), tendencia (media 28 / media 91), CV de 28 días, días atípicos en la ventana, último valor y media de 4 semanas del mismo día de la semana.
* **Prueba de no-fuga:** al recalcular la tabla con la serie truncada en el origen O se obtienen exactamente las mismas variables para O. Se verificó en 3 orígenes, incluido el primero de prueba.
* En cada origen solo se entrena con filas cuyo objetivo ya se había observado (`fecha_objetivo ≤ O`).
* **Hiperparámetros** (grilla de 12 combinaciones en el walk-forward): `num_leaves = 7`, 300 árboles, `learning_rate = 0.03`, pérdida **L1**, con un MAE medio por origen de 38.4 ± 19.6. La pérdida L1 ganó en todas las combinaciones, coherente con optimizar el MAE y con su robustez a días atípicos.

## B.7 Resultados

**Validación** (21 orígenes, sin días de paro):

| Modelo | MAE | RMSE | MAPE % | sMAPE % | Desv. MAE entre orígenes | Mejora vs. ing. est. |
|---|---|---|---|---|---|---|
| Ingenuo | 54.9 | 67.8 | 22.3 | 25.2 | 20.6 | −45 % |
| Ingenuo estacional | 37.9 | 49.7 | 16.3 | 16.8 | 13.6 | — |
| SARIMA | 34.9 | 44.0 | 15.6 | 15.1 | 16.0 | +8 % |
| **SARIMAX** | **29.0** | **36.5** | **12.4** | **12.3** | **10.7** | **+23 %** |
| LightGBM | 36.1 | 46.2 | 16.5 | 15.1 | 19.6 | +5 % |

→ **Modelo seleccionado: SARIMAX.** Es el más preciso y también el más estable entre orígenes.

**Prueba** (5 orígenes × 28 días; se usa una sola vez):

| Modelo | MAE | RMSE | MAPE % | sMAPE % | Mejora vs. ing. est. |
|---|---|---|---|---|---|
| Ingenuo | 77.6 | 94.1 | 32.3 | 37.7 | −17 % |
| Ingenuo estacional | 66.4 | 84.6 | 29.8 | 32.6 | — |
| SARIMA | 59.4 | 73.7 | 27.0 | 28.5 | +11 % |
| SARIMAX | 61.8 | 76.1 | 27.5 | 29.7 | +7 % |
| LightGBM | **53.5** | **66.5** | **26.8** | **24.6** | **+20 %** |

**Error por horizonte** (MAE por semana del horizonte, prueba; figuras `B_09_mae_horizonte_val.png` y `B_10_mae_horizonte_test.png`):

| Modelo | h 1–7 | h 8–14 | h 15–21 | h 22–28 |
|---|---|---|---|---|
| Ingenuo estacional | 50.9 | 65.5 | 75.1 | 74.1 |
| SARIMAX | **35.5** | 62.6 | 75.6 | 73.7 |
| LightGBM | 46.3 | **59.3** | **60.6** | **47.7** |

El error crece con el horizonte en todos los modelos. SARIMAX domina la primera semana (−30 % frente al ingenuo estacional); en horizontes largos LightGBM degrada menos.

**¿Por qué la prueba es más difícil?** (análisis *post hoc*, no usado para elegir modelos):

* La prueba contiene dos cambios de régimen sin precedentes en la historia: un **valle del 6 al 14 de julio** (−40 % aprox., que coincide con la eliminación de Brasil del Mundial el 6-jul; no tenemos evidencia externa de su causa) y un **salto de nivel en agosto** (de 204 a 280 órdenes/día, +38 %).
* Todos los modelos subestiman agosto: el sesgo medio va de −23 % (LightGBM) a −30 % (SARIMAX).
* El error se concentra en los orígenes del 8 y del 15 de julio, que pronostican desde el valle hacia el pico. En los orígenes de régimen estable (24-jun, 1-jul y 22-jul), SARIMA/SARIMAX superan a LightGBM (MAE de 29–45 frente a 40–49).
* En los días de partido de Brasil, SARIMA, SARIMAX y LightGBM sobreestiman la demanda (+33 % a +43 %).

**Lectura:** la selección por validación es correcta para el régimen típico. LightGBM, que modela la serie relativa a su nivel reciente, resultó más robusto ante el cambio de régimen. La diferencia de rendimiento entre validación y prueba es una limitación real que se reporta, no un error de método.

## B.8 Incertidumbre

* **Paramétrico (SARIMAX):** intervalos del modelo en log, transformados con `expm1`.
* **Conformal por horizonte (SARIMAX y LightGBM):** se calcula el cuantil `⌈(n+1)(1−α)⌉/n` del |residuo log| de validación, por separado para cada semana del horizonte.

| Método | Cobertura 80 % | Ancho medio 80 % | Cobertura 95 % | Ancho medio 95 % |
|---|---|---|---|---|
| SARIMAX paramétrico — validación | 97.1 | 158 | 100.0 | 248 |
| SARIMAX paramétrico — prueba | 54.3 | 126 | 75.0 | 197 |
| SARIMAX conformal — prueba | 39.3 | 77 | 51.4 | 116 |
| LightGBM conformal — prueba | 65.0 | 115 | 80.0 | 178 |

* En validación el intervalo paramétrico es **conservador**: sobrecubre porque el término integrado acumula varianza.
* En prueba todos los métodos **subcubren**. Los conformales se calibran con residuos de validación, que no contienen cambios de régimen como el de agosto, y la intercambiabilidad que supone el método conformal se rompe.
* **Recomendación:** recalibrar cada semana con una ventana móvil de residuos recientes (conformal adaptativo) y activar una alerta cuando la cobertura de las últimas 4 semanas caiga por debajo del 70 % (figura `B_12_intervalos.png`).

## B.9 Pronóstico operativo (20-ago a 16-sep-2018)

Se reajustó el SARIMAX con todos los datos hasta el 19-ago, con intervalo conformal calibrado en validación (figura `B_13_pronostico_operativo.png`; detalle diario en `resultados/B_pronostico_28d.csv`):

| Semana | Pronóstico | Intervalo 80 % |
|---|---|---|
| 20 a 26-ago | 1 806 | 1 509 – 2 162 |
| 27-ago a 2-sep | 1 813 | 1 529 – 2 148 |
| 3 a 9-sep (incluye Independência, 7-sep) | 1 770 | 1 421 – 2 203 |
| 10 a 16-sep | 1 813 | 1 438 – 2 284 |

*El intervalo semanal suma los extremos diarios, así que es conservador. Dada la subcobertura observada en prueba, conviene leerlo como un piso de incertidumbre.*

Este archivo alimenta la integración del Módulo D (ii): alertas diarias esperadas = demanda proyectada × tasa de alerta del modelo A.

## B.10 Extensión: São Paulo

Es la misma consulta con `estado = 'SP'` (41.7 % de las órdenes). Se usan la especificación SARIMAX y los hiperparámetros heredados de la serie nacional, sin reajustar. En prueba: ingenuo estacional MAE 37.0, SARIMAX 35.5 y **LightGBM 27.6** (sMAPE 29 %). El ranking replica el de la serie nacional y el error relativo es mayor, como se espera en una serie de menor volumen.

## B.11 Limitaciones y trabajo futuro

* **Cambio de régimen:** el modelo no conoce campañas comerciales, cambios de precios ni la entrada de nuevos vendedores. Lo más probable es que eso explique el salto de agosto. Agregar un calendario de campañas como exógena es la mejora con mayor potencial.
* **Pocos ciclos anuales** (~1.5 años): no se puede estimar una estacionalidad anual ni validar el pronóstico de un Black Friday fuera de la muestra. El coeficiente de BF se estima con una sola ocurrencia.
* **Truncamiento:** el pronóstico operativo no puede verificarse con los datos disponibles.
* **Intervalos:** subcubren ante cambios de régimen; se requiere recalibración adaptativa.
* **Trabajo futuro:** un ensamble SARIMAX + LightGBM, que combina la precisión de corto plazo del primero con la robustez del segundo en horizontes largos, validado con el mismo protocolo walk-forward. También un modelo jerárquico por estado o categoría con reconciliación de pronósticos.

---

## Anexo B — Bitácora de decisiones de diseño

| # | Decisión | Alternativas consideradas | Sustento |
|---|---|---|---|
| 1 | Contar todas las órdenes, sin filtrar por estado | Solo `delivered` | La pregunta es de demanda recibida; las canceladas también consumen capacidad. Canceladas y no disponibles son ~1.2 %. |
| 2 | Grilla `generate_series` + `LEFT JOIN` | `GROUP BY` simple | Lo exige el taller; sin los ceros, los rezagos y la estacionalidad quedarían desalineados. |
| 3 | Período 2017-01-01 a 2018-08-19 | Todo el dataset; cortar el 15-ago como en el Módulo A | 2016 es un piloto; desde el 22-ago hay truncamiento. El corte del 15-ago del Módulo A responde a censura de *entregas*, que no aplica a *compras*. Terminar en domingo deja 8 semanas completas. |
| 4 | Ajuste desde 2017-02-01 | Desde 2017-01-01 | Enero es el arranque (días con 0–35 órdenes); en log distorsiona la varianza. |
| 5 | Modelar en log(1+y) | Nivel original; Box-Cox | La amplitud semanal crece con el nivel; garantiza pronósticos positivos; log1p tolera los ceros. |
| 6 | Dummies para BF, post-BF, feriados y fiestas | Excluir o imputar esos días | Son recurrentes y con fecha conocida: hay que poder pronosticarlos. |
| 7 | Paro: dummy en el ajuste, 0 al pronosticar, fuera de las métricas de validación | Imputar; dejarlo tal cual | Imprevisible: no debe sesgar parámetros ni penalizar la selección. |
| 8 | Mundial solo como diagnóstico | Dummy en los modelos | Solo 2 ocurrencias antes de la prueba; las fechas de eliminatorias no se conocían. |
| 9 | Prueba con 5 orígenes semanales dentro de las 8 semanas | Un único pronóstico de 56 días | El horizonte pedido es 28 días; varios orígenes dan 5 observaciones por horizonte y simulan el reentrenamiento semanal. |
| 10 | Validación desde ene-2018, ventana expansiva | Ventana móvil; empezar en 2017 | Cada ajuste ya vio un Black Friday; con 1.5 años de datos no conviene descartar historia. |
| 11 | Selección por MAE (sin paro) | RMSE, MAPE | El MAE está en unidades de órdenes, que es lo que interpreta el planeador; es robusto a picos; MAPE y sMAPE se reportan como complemento. |
| 12 | SARIMAX con estacionalidad determinística | Diferencia estacional D = 1 | La familia E estima un MA estacional de −1 (no invertible); la D tiene residuos blancos y −15 % de MAE en validación. |
| 13 | AIC dentro de cada familia, walk-forward entre familias | AIC global | El AIC no es comparable con distinto orden de diferenciación. |
| 14 | LightGBM directo con el horizonte como variable | Recursivo; 28 modelos directos | Sin acumulación de error; todas las variables quedan en SQL; los horizontes comparten aprendizaje. |
| 15 | Objetivo y rezagos relativos a la media de 28 días | Niveles absolutos | Los árboles no extrapolan la tendencia. |
| 16 | Prueba explícita de no-fuga (serie truncada) | Confiar en el diseño de la consulta | Es evidencia verificable de que los rezagos no miran al futuro. |
| 17 | Pérdida L1 en LightGBM | L2 | Ganó en validación en todas las combinaciones; es coherente con optimizar el MAE. |
| 18 | Conformal por semana del horizonte | Un único cuantil; regresión cuantílica | No supone normalidad y el ancho crece con h; es comparable entre modelos. |
| 19 | Pronóstico operativo con SARIMAX, aunque LightGBM ganó la prueba | Cambiar a LightGBM | Cambiar de modelo después de ver la prueba sería *test snooping*; la prueba se usa una sola vez. El hallazgo queda como trabajo futuro (ensamble). |
