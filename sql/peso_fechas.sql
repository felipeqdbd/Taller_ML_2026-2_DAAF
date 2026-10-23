-- ============================================================================
-- peso_fechas.sql
-- Propósito:   Cuántas emisiones pronostican cada fecha objetivo (peso por solapamiento).
-- Operaciones:
--   1. Filtra las predicciones de un modelo.
--   2. Cuenta emisiones por fecha objetivo.
-- Parámetros:  1) nombre del modelo de referencia.
-- Requiere:    vista en memoria predicciones.
-- Salida:      una fila por fecha objetivo.
-- ============================================================================
SELECT fecha,count(*) AS emisiones FROM predicciones
WHERE modelo=? GROUP BY fecha ORDER BY fecha;
