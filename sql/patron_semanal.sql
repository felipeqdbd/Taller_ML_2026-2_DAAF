-- ============================================================================
-- patron_semanal.sql
-- Propósito:   Patrón semanal del historial inicial.
-- Operaciones:
--   1. Filtra la vista serie hasta la fecha de corte.
--   2. Agrupa por día ISO de la semana (1 = lunes ... 7 = domingo): días, media y mediana.
-- Parámetros:  1) fecha de corte.
-- Salida:      una fila por día de la semana.
-- ============================================================================
SELECT isodow(fecha) dia_semana, count(*) dias, avg(y) media, median(y) mediana
FROM serie WHERE fecha<=CAST(? AS DATE) GROUP BY 1 ORDER BY 1;
