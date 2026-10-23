-- ============================================================================
-- resumen_serie.sql
-- Propósito:   Resumen de la serie diaria del período útil.
-- Operaciones:
--   1. Toma la vista serie (salida de serie_diaria.sql).
--   2. Calcula rango de fechas, día final, número de días, total, mínimo, máximo
--      y días con cero órdenes.
-- Parámetros:  ninguno.
-- Requiere:    vista en memoria serie.
-- Salida:      una fila.
-- ============================================================================
SELECT min(fecha) AS desde,max(fecha) AS hasta,dayname(max(fecha)) AS dia_final,
       count(*) AS dias,sum(y) AS pedidos,min(y) AS minimo,max(y) AS maximo,
       count(*) FILTER (WHERE y=0) AS dias_cero
FROM serie;
