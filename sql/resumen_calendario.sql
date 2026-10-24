-- ============================================================================
-- resumen_calendario.sql
-- Propósito:   Días de cada tipo de evento por año en el calendario.
-- Operaciones:
--   1. Suma los indicadores 0/1 de la vista calendario agrupando por año.
-- Parámetros:  ninguno.
-- Salida:      una fila por año.
-- ============================================================================
-- Los indicadores pueden coincidir: Navidad es festivo y fin de año.
SELECT year(fecha) AS anio,count(*) AS dias_calendario,
       sum(festivo) AS dias_festivos_nacionales,
       sum(carnaval) AS dias_carnaval,
       sum(black_friday) AS dias_black_friday,
       sum(post_black_friday) AS dias_post_black_friday,
       sum(fin_anio) AS dias_fin_anio
FROM calendario GROUP BY 1 ORDER BY 1;
