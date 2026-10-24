-- ============================================================================
-- perfil_semanal.sql
-- Propósito:   Razón de cada día frente a la media centrada de su semana, sin eventos.
-- Operaciones:
--   1. Filtra la vista serie hasta la fecha de corte: la ventana no mira más allá.
--   2. Calcula la media de 7 días centrada (3 antes, el día, 3 después).
--   3. Descarta ventanas incompletas y las que contienen algún día con evento,
--      para que un pico no altere la razón de sus vecinos.
-- Parámetros:  1) fecha de corte.
-- Requiere:    vistas en memoria serie y etiquetas (etiquetas_eventos.sql).
-- Salida:      una fila por día válido: fecha, dia_semana (1 = lunes), y, media, razon.
-- ============================================================================
WITH tramo AS (
 SELECT s.fecha,s.y,
        CASE WHEN EXISTS(SELECT 1 FROM etiquetas e WHERE e.fecha=s.fecha) THEN 1 ELSE 0 END AS marcado
 FROM serie s WHERE s.fecha<=CAST(? AS DATE)
), centrada AS (
 SELECT fecha,y,avg(y) OVER v AS media_centrada_7,count(*) OVER v AS n_ventana,
        sum(marcado) OVER v AS marcados_ventana
 FROM tramo WINDOW v AS (ORDER BY fecha ROWS BETWEEN 3 PRECEDING AND 3 FOLLOWING)
)
SELECT fecha,isodow(fecha)::INTEGER AS dia_semana,y,media_centrada_7,
       y/media_centrada_7 AS razon
FROM centrada WHERE n_ventana=7 AND marcados_ventana=0 ORDER BY fecha;
