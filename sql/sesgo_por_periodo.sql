-- ============================================================================
-- sesgo_por_periodo.sql
-- Propósito:   Nivel real, nivel pronosticado y sesgo por mes de la fecha objetivo.
-- Operaciones:
--   1. Agrupa los pares de predicción por modelo y mes de la fecha objetivo.
--   2. Calcula pares, media real, media pronosticada, MAE y sesgo porcentual medio.
-- Parámetros:  ninguno.
-- Requiere:    vista en memoria predicciones.
-- Salida:      una fila por (modelo, mes). Lectura posterior: no se usa para decidir.
-- ============================================================================
SELECT modelo,date_trunc('month',fecha)::DATE AS mes,count(*) AS pares,
       avg(real) AS real_medio,avg(pred) AS pred_medio,avg(abs(real-pred)) AS MAE,
       avg(100*(pred-real)/real) AS sesgo_pct
FROM predicciones GROUP BY modelo,mes ORDER BY modelo,mes;
