-- ============================================================================
-- ejemplo_variables_evento.sql
-- Propósito:   Variables que recibe el modelo en un origen alrededor de un evento.
-- Operaciones:
--   1. Filtra la vista variables por un origen y un rango de fechas objetivo.
-- Parámetros:  1) origen; 2) primera fecha objetivo; 3) última fecha objetivo.
-- Salida:      una fila por horizonte.
-- ============================================================================
-- Lo que ve el modelo al cierre del origen sobre un evento de calendario.
SELECT origen,fecha,h,dia_semana,festivo,black_friday,
       post_black_friday,fin_anio,lag_0,media_28,real
FROM variables
WHERE origen=CAST(? AS DATE)
  AND fecha BETWEEN CAST(? AS DATE) AND CAST(? AS DATE)
ORDER BY h;
