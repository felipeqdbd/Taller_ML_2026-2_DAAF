-- ============================================================================
-- metricas_igual_peso_fecha.sql
-- Propósito:   Métricas donde cada fecha objetivo pesa igual, aunque reciba varias emisiones.
-- Operaciones:
--   1. Promedia por modelo y fecha las pérdidas de todas las emisiones que la pronosticaron.
--   2. Promedia después entre fechas: MAE, RMSE, MAPE y sMAPE.
-- Parámetros:  ninguno.
-- Requiere:    vista en memoria predicciones.
-- Salida:      una fila por modelo.
-- ============================================================================
WITH diario AS (
 SELECT modelo,fecha,avg(abs(real-pred)) AS mae,avg(pow(real-pred,2)) AS mse,
        avg(100*abs(real-pred)/real) AS mape,
        avg(CASE WHEN abs(real)+abs(pred)=0 THEN 0
                 ELSE 200*abs(real-pred)/(abs(real)+abs(pred)) END) AS smape
 FROM predicciones GROUP BY modelo,fecha
)
SELECT modelo,avg(mae) AS MAE,sqrt(avg(mse)) AS RMSE,avg(mape) AS MAPE,
       avg(smape) AS sMAPE,count(*) AS fechas
FROM diario GROUP BY modelo ORDER BY MAE;
