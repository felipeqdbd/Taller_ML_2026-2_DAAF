-- ============================================================================
-- resumen_perfil_semanal.sql
-- Propósito:   Resumen del perfil semanal por ventana de análisis y día de la semana.
-- Operaciones:
--   1. Agrupa las razones día / media centrada por ventana y día ISO de la semana.
--   2. Calcula días, media, mediana y desviación estándar de la razón.
-- Parámetros:  ninguno.
-- Requiere:    vista en memoria perfil (salida de perfil_semanal.sql con columna ventana).
-- Salida:      una fila por (ventana, día de la semana).
-- ============================================================================
SELECT ventana,dia_semana,count(*) AS dias,avg(razon) AS media,
       median(razon) AS mediana,stddev_samp(razon) AS desviacion
FROM perfil GROUP BY ALL ORDER BY ventana,dia_semana;
