-- ============================================================================
-- errores_por_evento.sql
-- Propósito:   Error de pronóstico en días con evento frente al resto, por etapa y modelo.
-- Operaciones:
--   1. Une cada par origen-horizonte con las etiquetas de evento de su fecha objetivo.
--   2. Los días sin etiqueta forman el grupo sin_evento; un día con dos etiquetas
--      (Navidad: festivo y fin_anio) cuenta en ambas.
--   3. Agrupa por etapa, modelo y evento: pares, fechas distintas, MAE, MAPE y sesgo.
-- Parámetros:  ninguno.
-- Requiere:    vistas en memoria predicciones (con columna etapa) y etiquetas.
-- Salida:      una fila por (etapa, modelo, evento).
-- ============================================================================
-- sesgo = pronóstico - real: positivo significa sobrepronóstico.
WITH marcadas AS (
 SELECT p.etapa,p.modelo,p.fecha,p.real,p.pred,coalesce(e.evento,'sin_evento') AS evento
 FROM predicciones p LEFT JOIN etiquetas e USING(fecha)
)
SELECT etapa,modelo,evento,count(*) AS pares,count(DISTINCT fecha) AS fechas,
       avg(abs(real-pred)) AS MAE,avg(100*abs(real-pred)/real) AS MAPE,
       avg(pred-real) AS sesgo
FROM marcadas GROUP BY etapa,modelo,evento ORDER BY etapa,modelo,MAE DESC;
