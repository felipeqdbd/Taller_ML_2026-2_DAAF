-- ============================================================================
-- diagnostico.sql
-- Propósito:   Medias móviles de 7 y 28 días para describir nivel y tendencia.
-- Operaciones:
--   1. Filtra la vista serie hasta la fecha de corte.
--   2. Calcula promedios con ventanas que terminan en el día actual (sin mirar al futuro).
-- Parámetros:  1) fecha de corte (en B_series_01_exploracion: primer origen de prueba).
-- Salida:      una fila por día: fecha, y, media_7, media_28.
-- ============================================================================
-- Ventanas causales: cada media usa solo el día y su pasado.
SELECT fecha,y,
 avg(y) OVER (ORDER BY fecha ROWS BETWEEN 6 PRECEDING AND CURRENT ROW) media_7,
 avg(y) OVER (ORDER BY fecha ROWS BETWEEN 27 PRECEDING AND CURRENT ROW) media_28
FROM serie WHERE fecha<=CAST(? AS DATE) ORDER BY fecha;
