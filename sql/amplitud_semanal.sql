-- ============================================================================
-- amplitud_semanal.sql
-- Propósito:   Relación entre el nivel semanal y la dispersión dentro de la semana.
-- Operaciones:
--   1. Filtra la vista serie hasta la fecha de corte.
--   2. Agrupa por semana lunes-domingo y conserva solo semanas completas.
--   3. Calcula media y desviación de y y de ln(1+y), y cuenta días con evento.
--   4. Etiqueta la semana como diagnostico si termina antes o en el fin de esa ventana.
-- Parámetros:  1) último día de la ventana de diagnóstico; 2) fecha de corte.
-- Requiere:    vistas en memoria serie y etiquetas (etiquetas_eventos.sql).
-- Salida:      una fila por semana completa.
-- ============================================================================
WITH parametros AS (
 SELECT CAST(? AS DATE) AS fin_diagnostico,CAST(? AS DATE) AS corte
), marcas AS (
 SELECT s.fecha,s.y,
        CASE WHEN EXISTS(SELECT 1 FROM etiquetas e WHERE e.fecha=s.fecha) THEN 1 ELSE 0 END AS marcado
 FROM serie s,parametros p WHERE s.fecha<=p.corte
), semanas AS (
 SELECT date_trunc('week',fecha)::DATE AS semana,count(*) AS dias,
        avg(y) AS media,stddev_samp(y) AS desviacion,
        avg(ln(1+y)) AS media_log,stddev_samp(ln(1+y)) AS desviacion_log,
        sum(marcado) AS dias_evento
 FROM marcas GROUP BY 1 HAVING count(*)=7
)
SELECT s.*,CASE WHEN s.semana+INTERVAL 6 DAY<=p.fin_diagnostico
                THEN 'diagnostico' ELSE 'posterior' END AS ventana
FROM semanas s,parametros p ORDER BY s.semana;
