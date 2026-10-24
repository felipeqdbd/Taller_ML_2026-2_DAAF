-- ============================================================================
-- esperado_mismo_dia.sql
-- Propósito:   Valor esperado de cada día: mediana del mismo día de la semana en las
--              cuatro semanas previas.
-- Operaciones:
--   1. Filtra la vista serie hasta la fecha de corte.
--   2. Toma los rezagos 7, 14, 21 y 28 (solo pasado) y calcula su mediana.
--   3. Une las etiquetas de eventos del día (puede haber varias).
-- Parámetros:  1) fecha de corte.
-- Requiere:    vistas en memoria serie y etiquetas (etiquetas_eventos.sql).
-- Salida:      una fila por día con al menos cuatro semanas previas.
-- ============================================================================
-- La mediana tolera que una de las cuatro semanas previas también sea atípica.
WITH base AS (
 SELECT fecha,y,lag(y,7) OVER w l7,lag(y,14) OVER w l14,lag(y,21) OVER w l21,lag(y,28) OVER w l28
 FROM serie WHERE fecha<=CAST(? AS DATE) WINDOW w AS (ORDER BY fecha)
)
SELECT b.fecha,isodow(b.fecha)::INTEGER AS dia_semana,b.y,
       list_median([b.l7,b.l14,b.l21,b.l28]) AS esperado,
       b.y/list_median([b.l7,b.l14,b.l21,b.l28]) AS razon,
       string_agg(e.evento,', ' ORDER BY e.evento) AS eventos
FROM base b LEFT JOIN etiquetas e USING(fecha)
WHERE b.l28 IS NOT NULL
GROUP BY b.fecha,b.y,b.l7,b.l14,b.l21,b.l28 ORDER BY b.fecha;
