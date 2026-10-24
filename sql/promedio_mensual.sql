-- ============================================================================
-- promedio_mensual.sql
-- Propósito:   Nivel mensual de la serie para describir la tendencia.
-- Operaciones:
--   1. Filtra la vista serie hasta la fecha de corte.
--   2. Agrupa por mes: días observados, órdenes y promedio diario.
-- Parámetros:  1) fecha de corte (primer origen de prueba).
-- Salida:      una fila por mes; el último puede estar incompleto (ver dias).
-- ============================================================================
SELECT date_trunc('month',fecha)::DATE AS mes,count(*) AS dias,
       sum(y) AS ordenes,avg(y) AS media_diaria
FROM serie WHERE fecha<=CAST(? AS DATE) GROUP BY 1 ORDER BY 1;
