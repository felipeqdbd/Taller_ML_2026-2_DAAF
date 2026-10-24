<!-- Fuente del informe. Las cifras se escriben como {{clave}} y salen de contexto.py. -->
<!-- Figuras: ::: figura archivo | alto en cm | pie. Tablas: ::: tabla clave | título | nota. -->

::: portada rotulo: Taller de Aprendizaje Automático · Módulo B · Series de tiempo | titulo: Pronóstico diario de órdenes de Olist a 28 días | subtitulo: Formulación, validación con origen móvil e intervalos de predicción para la planeación semanal | Autores: Daniel Ospina Pajoy ; Anlly Carolina Tabares Bedoya ; Albeiro Ceballos Cordoba ; Luis Felipe Quesada Bedoya | Profesor: Andres Vasquez Restrepo | Curso: Aprendizaje Automático, semestre 2026-2 | Programa: Msc. Ciencias de la ingeniería / Msc. Ciencia de los datos | Institución: Universidad EAFIT | Fecha: {{fecha_hoy}}

::: indice

::: salto

# 1. Resumen ejecutivo

Olist es un *marketplace* brasileño que conecta a pequeños vendedores con los grandes canales de comercio electrónico. Este trabajo resuelve el módulo de series de tiempo del taller, cuya pregunta de negocio es de planeación: ¿cuántas órdenes recibirá la plataforma en las próximas semanas? De esa cifra dependen el personal de atención al cliente, los acuerdos con transportadores y la capacidad que se reserva para los días de mayor carga. La respuesta es un pronóstico diario a 28 días, emitido al cierre de cada domingo a partir de las {{total_pedidos}} órdenes registradas entre el {{inicio}} y el {{fin}}.

::: recuadro Respuesta: órdenes esperadas del {{final_desde}} al {{final_hasta}}
::: tabla respuesta | Pronóstico semanal y su intervalo del 90 % nominal | El intervalo semanal se calibró con errores de totales semanales; no es la suma de los intervalos diarios.
::: fin

La demanda esperada ronda las {{semana_media}} órdenes por semana, {{total_final}} en las cuatro semanas. El modelo conserva el ritmo semanal de la serie: los lunes concentran la mayor carga (unas {{lunes_final}} órdenes) y los sábados la menor (unas {{sabado_final}}). El viernes 7 de septiembre, festivo nacional, baja a unas {{festivo_final}} órdenes, frente a las {{viernes_final}} de un viernes corriente.

El pronóstico proviene de un modelo SARIMAX con calendario: una regresión con errores ARIMA, ajustada sobre el logaritmo de la demanda, que incorpora el día de la semana y los eventos comerciales previsibles. Se eligió entre nueve candidatos por su error en 30 emisiones de validación, donde redujo el error absoluto medio en un {{mejora_sel}} frente a la línea base más exigente, que repite lo ocurrido la semana anterior. En las ocho semanas finales, reservadas como prueba, conservó la ventaja, aunque más estrecha ({{mejora_test}}): su error medio fue de {{mae_test_sem1}} órdenes diarias en la primera semana del horizonte y de unas {{mae_test_sem34}} en la tercera y la cuarta.

Los intervalos deben leerse con cautela. En la prueba, el intervalo diario del 90 % contuvo el valor real en el {{cob_dia}} de los casos, y el semanal en el {{cob_sem}}, porque en agosto de 2018 la demanda subió un {{salto_ago}} respecto de julio sin un antecedente que permitiera anticiparlo. Se recomienda reajustar el modelo cada domingo, dimensionar la capacidad de la semana siguiente con el pronóstico y su límite superior, y tratar las semanas tres y cuatro como orientativas. El ejercicio es retrospectivo: usa datos públicos de 2017 y 2018 y no es una proyección actual de la empresa.

::: salto

# 2. Datos, modelo relacional y decisiones de calidad

El conjunto de datos público de Olist reúne unas cien mil órdenes anonimizadas con información de clientes, productos, vendedores, pagos, envíos y reseñas. Se cargó en DuckDB con el script del curso, en {{n_tablas}} tablas que suman {{filas_total}} filas, y todo el acceso posterior se hizo con consultas SQL de solo lectura guardadas en `sql/`, con las fechas de corte como parámetros.

## 2.1 Unidad de análisis y modelo relacional

La pregunta de negocio se refiere a órdenes recibidas, de modo que la unidad de análisis es la orden de compra y su fecha es el instante en que el cliente la realizó (`order_purchase_timestamp`). Como muestra la [[fig:modelo_relacional]], la tabla `orders` ocupa el centro del modelo: cada orden tiene un identificador único y se relaciona uno a uno con su cliente, pero uno a muchos con sus artículos, pagos y reseñas. Si se contaran filas después de unir órdenes con artículos y pagos, la misma compra aparecería varias veces: la unión produce {{filas_join}} filas para {{ordenes}} órdenes. Por eso la serie se cuenta directamente en `orders`, antes de cualquier unión.

::: figura modelo_relacional | 8.6 | Modelo relacional del conjunto de datos de Olist. Cada caja es una tabla, con su número de filas y sus llaves principales (PK) y foráneas (FK); las líneas indican la llave de unión y su cardinalidad. La serie se cuenta solo en `orders` (azul); `customers` (violeta) se usa únicamente en la exploración geográfica.

## 2.2 Calidad y período útil

La [[tab:calidad]] resume las comprobaciones que afectan a la serie. El criterio fue no descartar una orden por un problema que no invalida ni su existencia ni su fecha de compra: una orden sin artículos registrados o con una diferencia de centavos entre artículos y pagos es un defecto del extracto, no una compra inexistente. Por la misma razón se incluyen todas las órdenes, cualquiera sea su estado final; las {{canceladas}} canceladas y las {{indisponibles}} indisponibles también representan demanda que llegó a la plataforma.

::: tabla calidad | Comprobaciones de calidad relevantes para la serie y decisión adoptada

El extracto no tiene la misma cobertura en todo su rango. En 2016 los registros son escasos y discontinuos, propios de un período de arranque. Hasta mediados de agosto de 2018 se registran entre 200 y 370 órdenes diarias con el patrón semanal habitual, pero a partir del 22 de agosto la cifra cae día tras día hasta casi cero: es el corte del extracto, no un colapso de la demanda. Por eso el período útil va del {{inicio}} al {{fin}}, el último domingo anterior al corte, de modo que cada pronóstico cubra cuatro semanas completas de lunes a domingo. La serie se construyó en SQL sobre un calendario completo, para que un día sin órdenes apareciera con valor cero en lugar de desaparecer: resultan {{n_dias}} días consecutivos y {{total_pedidos}} órdenes, sin días vacíos.

# 3. Módulo B: series de tiempo

## 3.1 Formulación y protocolo de evaluación

Sea $y_t$ el número de órdenes compradas el día $t$. Al cierre de un domingo $o$, llamado *origen*, se dispone de la historia $y_1, \dots, y_o$ y se desea pronosticar $y_{o+h}$ para cada horizonte $h = 1, \dots, 28$; cada conjunto de 28 pronósticos es una *emisión*. El horizonte de cuatro semanas responde al ciclo de planeación, y los orígenes en domingo garantizan que la primera semana pronosticada empiece un lunes. Como el valor de hoy depende del de ayer y del mismo día de la semana anterior, las observaciones no pueden barajarse, y el único error relevante es el de un pronóstico emitido con la información disponible en el origen.

Para reproducir el uso real se empleó una validación con origen móvil (*walk-forward*) y ventana expansiva: en cada origen el modelo se reentrena con toda la historia hasta ese domingo, emite sus 28 pronósticos y el origen avanza una semana. Las emisiones se repartieron en tres etapas sin fechas objetivo en común ([[fig:protocolo_temporal]]). La **validación** ({{n_sel}} emisiones, desde el {{primer_origen_sel}}) sirve solo para elegir el modelo; la **calibración** ({{n_cal}} emisiones, desde el {{primer_origen_cal}}) estima los intervalos con errores que no intervinieron en esa elección, y la **prueba** ({{n_prueba}} emisiones, desde el {{primer_origen_prueba}}) mide el desempeño una única vez.

::: figura protocolo_temporal | 5.2 | Esquema de validación con origen móvil. Cada fila es una emisión: la línea gris es la historia usada para ajustar, que crece con cada origen, y la barra de color son los 28 días pronosticados (azul: validación; verde: calibración; naranja: prueba). La franja violeta indica los datos usados para decidir la forma de los modelos.

La forma de los modelos se decidió únicamente con los {{dias_especif}} días anteriores al primer origen de validación; los datos de prueba no se consultaron en ninguna decisión. El costo de esta disciplina es que las primeras emisiones de validación se ajustan con menos de seis meses de datos y nunca han visto un Black Friday.

## 3.2 Análisis de la serie

La [[fig:serie_tendencia]] muestra la serie hasta el inicio de la prueba. Durante 2017 la media diaria pasó de unas {{feb17}} órdenes en febrero a unas {{oct17}} en octubre, y desde enero de 2018 se estabilizó en una meseta de entre {{meseta_min}} y {{meseta_max}}. Un modelo con tendencia lineal fija extrapolaría un crecimiento que ya no ocurre; por eso ningún modelo estadístico incluye deriva y la tendencia de ETS se amortigua con el horizonte.

::: figura serie_tendencia | 5.4 | Órdenes diarias (gris) y media móvil causal de 28 días (azul) hasta el primer origen de prueba. Las franjas indican la etapa de cada tramo de fechas; la zona rayada es la prueba, que no se examinó durante el análisis.

Para aislar la estacionalidad semanal, cada día se dividió por la media de los siete días centrados en él, sin semanas con eventos ([[fig:perfil_semanal]]). El lunes queda un {{lun_pct}} por encima de su semana y el sábado un {{sab_pct}} por debajo, con medianas casi idénticas entre la ventana de especificación y toda la historia previa a la prueba, aunque el nivel casi se cuadruplicó. Un patrón estable admite representarse con un indicador fijo por día. Además, el efecto es multiplicativo: la dispersión de cada semana crece con su nivel (correlación de {{r_orig}}) y deja de hacerlo tras aplicar $\log(1+y)$ ({{r_log}}). Por eso los modelos estadísticos se ajustan en esa escala; al invertirla, el pronóstico corresponde a la mediana, coherente con evaluar mediante el error absoluto.

::: figura perfil_semanal | 4.6 | Razón entre las órdenes de cada día y la media de su semana centrada, sin días con evento. En violeta, la ventana de especificación; en gris, toda la historia previa a la prueba. Un valor de 1 corresponde a un día promedio de su semana.

La descomposición STL robusta de $\log(1+y)$ ([[fig:stl_inicial]], Anexo C) confirma una tendencia creciente y un componente semanal de amplitud estable; su residuo solo destaca el lunes de Carnaval de 2017 y el 21 de junio de 2017, un día con {{y_junio}} órdenes que ningún calendario explica. Para decidir la diferenciación se combinaron dos pruebas con hipótesis nulas opuestas ([[tab:adf]]): la de Dickey-Fuller aumentada (ADF) supone una raíz unitaria y la KPSS, estacionariedad. Ambas coinciden en que el nivel no es estacionario y la primera diferencia sí, de modo que basta $d = 1$; la diferencia semanal también resulta estacionaria, así que las pruebas no eligen entre ambas.

::: tabla adf | Pruebas de estacionariedad sobre $\log(1+y)$ en la ventana de especificación | KPSS solo reporta su valor p entre 0,01 y 0,10; fuera de ese rango se indica el límite.

La elección la resolvieron la autocorrelación y la comparación de modelos. En las funciones ACF y PACF ([[fig:acf_pacf_inicial]], Anexo C), la primera diferencia conserva picos cada siete días; al descontar los indicadores de día y de eventos desaparecen y queda una correlación negativa en el primer rezago, propia de una media móvil de orden uno. Con el criterio de Akaike, ARIMA(1,1,1) quedó a {{delta_aic}} puntos del mejor orden, una diferencia que suele considerarse equivalente, y al forzar una diferencia estacional su coeficiente de media móvil se situó entre {{ma_est_min}} y {{ma_est_max}}: un valor cercano a −1 anula esa diferencia e indica que la semana es determinística. Con esta evidencia se fijó, antes de cualquier validación, el modelo principal:

::: ecuacion sarimax | \ln(1+y_t)=\sum_{k=1}^{6}\beta_k\,D_{k,t}+\sum_{j=1}^{5}\gamma_j\,E_{j,t}+u_t,\qquad (1-\phi B)(1-B)\,u_t=(1+\theta B)\,\varepsilon_t

donde $D_{k,t}$ son los indicadores de lunes a sábado (el domingo es la referencia), $E_{j,t}$ los cinco indicadores de eventos, $B$ el operador de rezago y $u_t$ un error ARIMA(1,1,1).

## 3.3 Eventos atípicos

Cada episodio se trató según una regla fijada antes de mirar magnitudes: **modelar** con un indicador si su fecha se conoce antes de emitir el pronóstico, **marcar** si no podía anticiparse (se mide su efecto sin dar al modelo información futura) y **excluir** solo los datos que no representan demanda. La magnitud se midió frente a un valor esperado, la mediana del mismo día de la semana en las cuatro semanas previas ([[tab:eventos]]; [[fig:eventos_atipicos]], Anexo C).

::: tabla eventos | Magnitud de cada episodio y tratamiento adoptado | Razón entre lo observado y lo esperado en el conjunto de días del episodio.

Black Friday fue el mayor ({{bf_obs}} órdenes frente a unas {{bf_esp}} esperadas) y su efecto se arrastra cuatro días; el fin de año redujo la demanda a la mitad durante toda la semana. Los festivos tienen un efecto medio de × {{fest_razon}}, muy variable (de × {{fest_min}} a × {{fest_max}}). Carnaval, que no es festivo nacional, se incorporó porque su fecha depende de la Pascua y su efecto ya era visible en febrero de 2017. La caída de la semana previa a Navidad (× {{prenav_razon}}) solo se observó en diciembre de 2017, dentro de la validación, y se documentó como limitación para no especificar el modelo con datos de evaluación. La huelga de camioneros de mayo de 2018 se marcó y se conservó en las métricas: no podía anticiparse, pero la operación real también enfrenta choques así.

## 3.4 Variables, fuga de información y estrategia multipaso

El modelo de aprendizaje automático, LightGBM, es un conjunto de árboles potenciados por gradiente que necesita ejemplos supervisados. Cada ejemplo es un par (origen, horizonte): sus entradas describen la historia al cierre del origen y el calendario de la fecha objetivo, y su salida es la demanda de ese día ([[tab:variables]]). Todas las variables se calculan en SQL con ventanas que terminan en el origen.

::: tabla variables | Variables del modelo LightGBM

Contra la fuga de información, en cada ajuste solo entran ejemplos cuya **fecha objetivo** sea anterior o igual al origen: un ejemplo emitido ayer a 28 días apunta a una etiqueta todavía desconocida. El calendario futuro sí se conoce; las ventas futuras, no. La auditoría del proyecto lo verifica reconstruyendo la serie sin las compras posteriores a dos orígenes y comprobando que los nueve modelos producen los mismos pronósticos.

Los 28 valores pueden obtenerse de forma **recursiva**, reutilizando cada predicción como dato para la siguiente, o **directa**, aprendiendo cada horizonte desde el origen. Los modelos estadísticos son recursivos: el filtro de Kalman propaga su estado con el calendario futuro conocido. LightGBM usa una estrategia **directa global**, con un único modelo que recibe el horizonte $h$ como variable; así no acumula sus propios errores y comparte entre horizontes lo aprendido sobre la semana y los eventos.

## 3.5 Modelos comparados y métricas

La [[tab:candidatos]] resume los nueve candidatos, fijados antes de evaluar. La línea base estacional, que repite el mismo día de la semana anterior, es exigente porque captura el ritmo semanal sin estimar nada. La variante SARIMAX sin eventos no busca ganar, sino medir cuánto aporta modelar los eventos. Las cuatro variantes de LightGBM comparten 300 árboles de siete hojas, pérdida L1 y semilla fija, y cruzan el conjunto de variables con el objetivo: absoluto, o relativo al nivel reciente, definido como el logaritmo de la razón entre la demanda del día objetivo y la media de los 28 días previos al origen.

::: tabla candidatos | Modelos candidatos y estrategia con que producen los 28 pronósticos | La equivalencia con los identificadores del código figura en el Anexo B.

Las métricas se calculan sobre los pares origen-horizonte, en órdenes por día:

::: ecuacion mae_rmse | \mathrm{MAE}=\frac{1}{N}\sum_{i=1}^{N}|y_i-\hat{y}_i|,\qquad \mathrm{RMSE}=\sqrt{\frac{1}{N}\sum_{i=1}^{N}(y_i-\hat{y}_i)^2}

::: ecuacion mape | \mathrm{MAPE}=\frac{100}{N}\sum_{i=1}^{N}\frac{|y_i-\hat{y}_i|}{y_i},\qquad \mathrm{sMAPE}=\frac{200}{N}\sum_{i=1}^{N}\frac{|y_i-\hat{y}_i|}{|y_i|+|\hat{y}_i|}

El MAE es el criterio de selección porque responde a la pregunta operativa: por cuántas órdenes se equivoca el plan en un día típico. El RMSE penaliza más los errores grandes; MAPE y sMAPE expresan el error en términos relativos (no hay días con cero órdenes en los períodos evaluados). Se informa también el sesgo, la media de $\hat{y}_i - y_i$. Como las emisiones se solapan, los errores no son independientes y no se presentan pruebas de significancia entre modelos.

## 3.6 Resultados

En validación ([[tab:validacion]]), el SARIMAX con calendario obtuvo el menor error: {{mae_sel_g}} órdenes diarias, un {{mejora_sel}} menos que la línea base estacional ({{mae_sel_est}}) y un {{mejora_sel_ing}} menos que la ingenua, y fue también el más estable entre orígenes (desviación de {{desv_g}} frente a {{desv_est}}). En todos los modelos el RMSE duplica al MAE por unos pocos errores enormes: Black Friday de 2017 se pronosticó desde cuatro orígenes que nunca habían visto uno y no se eliminó de la evaluación.

::: tabla validacion | Desempeño en validación: 30 emisiones × 28 horizontes, ordenado por MAE | MAE, RMSE y sesgo en órdenes por día; MAPE y sMAPE en %. Mejora: reducción porcentual del MAE frente a la línea base estacional. La barra azul señala el modelo elegido.

Las comparaciones de un solo factor explican parte del resultado. Añadir los indicadores de eventos redujo el MAE del SARIMAX en {{d_eventos}} órdenes y lo mejoró en {{o_eventos}} de 30 orígenes. En LightGBM, el objetivo relativo empeoró el error (+{{d_rel_base}} órdenes con variables básicas); una explicación compatible, aunque no aislada por el experimento, es que la media de 28 días deja de representar el nivel futuro cuando este cambia con rapidez. La prueba de Ljung-Box rechazó la ausencia de autocorrelación residual a siete rezagos en {{lb_rech}} de {{lb_n}} emisiones, de modo que queda estructura semanal sin capturar y el intervalo paramétrico tenderá a ser optimista.

La [[fig:metricas_horizonte_seleccion]] muestra cómo crece el error con el horizonte. El MAE del modelo elegido pasa de unas {{mae_h1}} órdenes en $h = 1$ a unas {{mae_h_final}} entre $h = 22$ y $h = 28$, y su MAPE, de un {{mape_h1}} % a un {{mape_h_final}} %; por semana del horizonte, el MAE es de {{sem_sel}} órdenes, siempre entre un {{mejora_sem_min}} y un {{mejora_sem_max}} por debajo de la línea base estacional. Los picos en $h$ = 5, 12, 19 y 26 son una sola fecha: Black Friday, vista desde cuatro orígenes.

::: figura metricas_horizonte_seleccion | 4.8 | Error por horizonte en validación (30 emisiones por cada $h$): MAE y RMSE en órdenes por día, MAPE en %. Cada modelo tiene color, tipo de línea y marcador propios; la línea gruesa azul es el modelo elegido.

En la prueba, entre el {{prueba_desde}} y el {{prueba_hasta}}, el modelo elegido ya estaba fijado ([[tab:prueba]]). Obtuvo un MAE de {{mae_test_g}} órdenes, un {{mejora_test}} mejor que la línea base estacional ({{mae_test_est}}). El ETS amortiguado logró un error algo menor ({{mae_test_mejor}}), pero la diferencia, inferior a una orden diaria, es mucho menor que la variación entre emisiones (desviación de {{desv_test}}) y no justifica cambiar de modelo a posteriori. Ningún LightGBM superó a la línea base estacional.

::: tabla prueba | Desempeño en prueba: 5 emisiones × 28 horizontes, ordenado por MAE | Mismas unidades que la [[tab:validacion]]. El modelo elegido (barra azul) se fijó antes de consultar esta tabla.

Todos los modelos subpronosticaron en la prueba (sesgo de {{sesgo_test_g}} órdenes diarias para el elegido). La ventaja se concentra en la primera semana del horizonte ({{mae_test_sem1}} órdenes frente a {{mae_test_est_sem1}} de la línea base estacional); en las semanas tres y cuatro, el error de todos los modelos ronda las {{mae_test_sem34}} órdenes. Entre el 6 y el 14 de julio la demanda cayó a entre 90 y 150 órdenes, y en agosto el nivel medio subió de {{real_jul}} a {{real_ago}} órdenes diarias: el sesgo del modelo elegido pasó de {{sesgo_jul}} en julio a {{sesgo_ago}} en agosto. Son errores de nivel, no de forma semanal. Que el valle coincida con la fase eliminatoria del Mundial, o que el salto obedezca a campañas comerciales, son hipótesis que los datos no permiten verificar.

## 3.7 Incertidumbre

Se compararon cuatro intervalos del 90 % nominal, fijados antes de la prueba. El **paramétrico** del SARIMAX se obtiene de la varianza de pronóstico del filtro de Kalman y supone errores normales e independientes. Los tres **conformales** no suponen una distribución: usan los errores de las doce emisiones de calibración. Para cada semana $s$ del horizonte se ordenan los {{n_err}} errores relativos $|y-\hat{y}|/(1+\hat{y})$ y se toma el de rango $k$:

::: ecuacion conformal | \hat{y}_{o+h}\pm\hat{q}_s\,(1+\hat{y}_{o+h}),\qquad \hat{q}_s=e_{s,(k)},\quad k=\lceil (n+1)(1-\alpha)\rceil

Con $n$ = {{n_err}} y $\alpha$ = 0,10, el rango es $k$ = {{rango_77}}. El intervalo principal es el conformal relativo del modelo elegido, cuyo ancho crece con el nivel, en coherencia con la serie multiplicativa. Su cuantil fue de {{q1}} en la primera semana y de entre {{q_resto_min}} y {{q_resto_max}} en las siguientes; sin los días de huelga, que caen en la calibración, el de la primera semana habría bajado a {{q1_sin_huelga}}.

::: tabla intervalos | Cobertura empírica y amplitud de los intervalos diarios en prueba | Cobertura: proporción de valores reales dentro del intervalo; nivel nominal del 90 %. Amplitud en órdenes por día.

Ningún intervalo alcanzó el 90 %. El conformal principal cubrió el {{cob_dia}} de los días y {{cub_sem}} de {{n_sem}} totales semanales; el paramétrico, el {{cob_param}} (ya en la calibración había quedado en el {{cob_param_cal}}, coherente con la autocorrelación residual). El conformal absoluto llegó al {{cob_abs}} con intervalos más anchos, pero elegirlo ahora sería ajustar el método con la prueba. La cobertura es alta en la primera semana y se degrada con la anticipación, porque los errores de calibración, de marzo a junio, no contenían un valle ni un salto de nivel como los de julio y agosto.

# 4. Interpretabilidad, integración y caso de uso

## 4.1 Qué aprendió el modelo elegido

Los coeficientes del SARIMAX con calendario se leen directamente: como el modelo está en escala logarítmica, $\exp(\beta)-1$ es el efecto porcentual aproximado de cada indicador ([[tab:coeficientes]]). Frente al domingo, el lunes vende un {{ef_lun}} más y el sábado un {{ef_sab}} menos; la cifra no contradice el {{lun_pct}} de la sección 3.2, porque allí la referencia era el promedio de la semana y aquí el domingo, que está por debajo de él. Black Friday multiplica la demanda por {{ef_bf}}, sus cuatro días posteriores la elevan un {{ef_post}}, y el fin de año, un festivo y Carnaval la reducen un {{ef_fin}}, un {{ef_fest}} y un {{ef_carn}}. Son asociaciones históricas, no efectos causales.

::: tabla coeficientes | Coeficientes del SARIMAX con calendario ajustado con toda la historia útil | Efecto aproximado = exp(coeficiente) − 1, frente al domingo para los días y frente a un día sin evento para los indicadores.

La [[tab:errores_evento]] juzga las decisiones de la sección 3.3 por sus consecuencias. Modelar los eventos redujo el error en los festivos (de {{err_fest_sin}} a {{err_fest_con}} órdenes) y en el fin de año (de {{err_fin_sin}} a {{err_fin_con}}); incluso la semana previa a Navidad mejoró (de {{err_prenav_sin}} a {{err_prenav_con}}), porque sin indicadores el pico de Black Friday se absorbe como una subida de nivel. Black Friday no pudo anticiparse en ninguna variante, y Carnaval empeoró (de {{err_carn_sin}} a {{err_carn_con}}) porque su coeficiente se estimó con un único antecedente, más intenso que el de 2018.

::: tabla errores_evento | MAE en validación por tipo de día, en órdenes por día | Fechas: días distintos con esa etiqueta entre los objetivos de validación. Un día con dos etiquetas cuenta en ambas.

En LightGBM, la importancia por ganancia se concentra en el índice de tiempo ({{tendencia_pct}}) y el día de la semana ({{dia_semana_pct}}), mientras rezagos y medias móviles casi no intervienen ([[fig:importancia_variables]]). El modelo aprendió el nivel de cada período a través del índice de tiempo, que un árbol no puede extrapolar: es una explicación plausible, aunque no demostrada, de que no siguiera el salto de agosto.

::: figura importancia_variables | 4.4 | Importancia por ganancia del mejor LightGBM de validación (variables básicas y objetivo absoluto), como proporción de la ganancia total.

## 4.2 Integración y caso de uso

El pronóstico se produce con un flujo que puede ejecutarse cada semana sin intervención manual. Las consultas de `sql/` construyen la serie, el calendario y la tabla de variables; `src/modelos.py` ajusta los candidatos y emite los 28 pronósticos, y `src/evaluacion.py` calcula métricas e intervalos. Los resultados se exportan en un archivo diario y otro semanal, con el pronóstico y sus límites, y cada ejecución termina con una auditoría independiente cuyos {{n_auditoria}} grupos de comprobaciones terminaron sin discrepancias.

Al cierre del domingo {{fin}}, el equipo de planeación recibe el pronóstico de la semana del {{final_desde}}: {{sem1_final}} órdenes, con un intervalo de {{sem1_inf}} a {{sem1_sup}}. Con el total dimensiona la atención al cliente y los acuerdos con transportadores, usa el límite superior para la capacidad flexible y, con el perfil diario de la [[fig:pronostico_final]], distribuye turnos, porque de lunes a miércoles se concentra la carga. Para las semanas tres y cuatro reserva capacidad ajustable. Si el total real de una semana sale del intervalo, o el sesgo de dos semanas seguidas supera el 15 %, el modelo se revisa antes de la siguiente emisión; las campañas comerciales y los choques que el modelo no conoce deben comunicarse al planeador por separado.

::: figura pronostico_final | 5.0 | Pronóstico de las cuatro semanas siguientes al último domingo observado. En negro, las últimas ocho semanas de historia; en azul, el pronóstico con su intervalo diario conformal del 90 % (banda); en violeta punteado, el intervalo paramétrico del SARIMAX.

# 5. Limitaciones, conclusiones y trabajo futuro

## 5.1 Limitaciones

La historia es corta: {{n_dias}} días, con una sola ocurrencia útil de Black Friday y dos de Carnaval, de modo que las magnitudes de esos eventos son inciertas. La prueba contiene dos cambios de nivel sin antecedente que ningún modelo ni intervalo anticipó. Las emisiones se solapan y los errores están correlacionados, por lo que las diferencias pequeñas entre modelos no son superioridad estadística. La evaluación es retrospectiva, aunque ninguna decisión se tomó con las fechas de prueba, y la base no registra campañas, precios ni inventario, que probablemente explican parte de los cambios de nivel.

## 5.2 Conclusiones

La respuesta a la pregunta de planeación es un pronóstico de unas {{semana_media}} órdenes por semana entre el {{final_desde}} y el {{final_hasta}}, confiable en su forma semanal y en la primera semana del horizonte, y orientativo para las semanas tres y cuatro. Un modelo estadístico relativamente simple, especificado a partir del diagnóstico de la serie, superó a todas las alternativas en validación y mantuvo la ventaja en la prueba: la escala logarítmica respeta el carácter multiplicativo de la demanda, los indicadores de día capturan una semana estable y los de eventos evitan que los picos contaminen el nivel. LightGBM no aprovechó su flexibilidad con esta historia, lo que no descarta el aprendizaje automático, sino que muestra que con estos datos no añade información que el modelo estadístico no capture. La incertidumbre debe comunicarse con la misma disciplina que el pronóstico puntual: los intervalos son nominales y resultaron optimistas.

## 5.3 Trabajo futuro

- Recalibrar los intervalos cada semana con errores recientes (predicción conformal adaptativa).
- Incorporar variables de campañas comerciales y medios de pago que anticipen saltos de nivel.
- Retirar el índice de tiempo de LightGBM o anclar su objetivo a un nivel más robusto, y reevaluarlo.
- Validar con un segundo diciembre un indicador para la semana previa a Navidad.

::: anexos

# Anexo A. Reproducibilidad

El proyecto se reproduce desde su raíz con cinco órdenes:

- `pip install -r requirements.txt`, con las versiones exactas registradas también en `resultados/entorno.json`;
- `python scripts/build_olist_duckdb.py --out data/olist.duckdb`, el script del curso (el archivo `.duckdb` no se entrega);
- `python scripts/ejecutar.py`, que ejecuta en orden los notebooks `00_datos`, `B_series_01_exploracion` y `B_series_02_modelado`;
- `python scripts/auditar.py`, que verifica los resultados de forma independiente;
- `python scripts/generar_documentacion.py`, que produce este informe a partir de `resultados/`.

LightGBM usa semilla fija (`random_state=2026`) y modo determinista, las rutas son relativas y las consultas SQL reciben sus fechas como parámetros.

# Anexo B. Auditoría y equivalencias

::: tabla auditoria | Comprobaciones independientes de scripts/auditar.py
::: tabla glosario | Equivalencia entre los nombres del texto y los identificadores del código

# Anexo C. Figuras de diagnóstico

::: figura stl_inicial | 6.4 | Descomposición STL robusta de $\log(1+y)$ en la ventana de especificación (febrero a julio de 2017): serie, tendencia, componente semanal y residuo. Se señalan el Carnaval de 2017 y la caída sin explicación del 21 de junio.
::: figura acf_pacf_inicial | 7.6 | ACF (izquierda) y PACF (derecha) en la ventana de especificación: nivel de $\log(1+y)$, su primera diferencia y la primera diferencia sin el efecto de los indicadores de día y de eventos. La banda sombreada es el intervalo aproximado del 95 % bajo ausencia de autocorrelación.
::: figura eventos_atipicos | 10.5 | Observado (línea negra) frente a esperado (línea discontinua: mediana del mismo día en las cuatro semanas previas) alrededor de cuatro episodios. Los puntos naranjas son los días con evento.
