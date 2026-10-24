-- ============================================================================
-- eda_clientes.sql
-- Propósito:   Frecuencia de compra del cliente real (customer_unique_id).
-- Operaciones:
--   1. Une customers con orders y cuenta órdenes distintas por customer_unique_id.
--   2. Agrupa a los clientes según su número de compras.
-- Parámetros:  ninguno.
-- Salida:      una fila por número de compras: compras, clientes.
-- ============================================================================
WITH frecuencia AS (
 SELECT customer_unique_id,count(DISTINCT order_id) compras FROM customers JOIN orders USING(customer_id) GROUP BY 1)
SELECT compras,count(*) clientes FROM frecuencia GROUP BY 1 ORDER BY 1;