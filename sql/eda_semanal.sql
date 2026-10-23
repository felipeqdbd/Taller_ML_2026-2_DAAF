-- ============================================================================
-- eda_semanal.sql
-- Propósito:   Órdenes por semana en toda la base.
-- Operaciones:
--   1. Trunca la fecha de compra a la semana (date_trunc('week') empieza el lunes)
--      y cuenta las órdenes de cada semana.
-- Parámetros:  ninguno.
-- Salida:      una fila por semana: semana (lunes de inicio), ordenes.
-- ============================================================================
SELECT date_trunc('week',order_purchase_timestamp)::DATE semana,count(*) ordenes FROM orders GROUP BY 1 ORDER BY 1;