-- ============================================================================
-- estados.sql
-- Propósito:   Distribución de las órdenes por estado final (order_status).
-- Operaciones:
--   1. Agrupa orders por order_status y cuenta las órdenes de cada estado.
-- Parámetros:  ninguno.
-- Salida:      una fila por estado, de mayor a menor número de órdenes.
-- ============================================================================
SELECT order_status,count(*) ordenes FROM orders GROUP BY 1 ORDER BY 2 DESC;