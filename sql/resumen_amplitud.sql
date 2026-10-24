-- ============================================================================
-- resumen_amplitud.sql
-- Propósito:   ¿La dispersión semanal depende del nivel? Comparación en escala
--              original y en ln(1+y).
-- Operaciones:
--   1. Descarta semanas con algún día de evento (alterarían la dispersión).
--   2. Agrupa por ventana: semanas, correlación nivel-dispersión en ambas escalas
--      y coeficiente de variación medio.
-- Parámetros:  ninguno.
-- Requiere:    vista en memoria amplitud (salida de amplitud_semanal.sql).
-- Salida:      una fila por ventana.
-- ============================================================================
SELECT ventana,count(*) AS semanas,
       corr(media,desviacion) AS corr_original,
       corr(media_log,desviacion_log) AS corr_log,
       avg(desviacion/media) AS cv_medio
FROM amplitud WHERE dias_evento=0 GROUP BY ventana ORDER BY ventana;
