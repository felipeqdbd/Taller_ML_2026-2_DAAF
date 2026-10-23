-- ============================================================================
-- cola.sql
-- Propósito:   Detalle diario del final de la base, para justificar el corte de cobertura.
-- Operaciones:
--   1. Filtra las compras desde la fecha indicada y cuenta órdenes por día.
-- Parámetros:  1) fecha inicial de la inspección.
-- Salida:      una fila por día con compras: fecha, ordenes.
-- ============================================================================
SELECT CAST(order_purchase_timestamp AS DATE) fecha,count(*) ordenes
FROM orders WHERE order_purchase_timestamp>=CAST(? AS DATE) GROUP BY 1 ORDER BY 1;