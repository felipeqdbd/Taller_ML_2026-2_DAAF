-- =====================================================================
-- Módulo B · Consulta 2: calendario y eventos atípicos
-- ---------------------------------------------------------------------
-- Una fila por día con variables de calendario y banderas de eventos.
-- Se usa como variables exógenas del SARIMAX y como variables de la
-- fecha objetivo en el modelo de ML. Puede extenderse más allá del
-- último dato observado (las fechas futuras son conocidas de antemano),
-- lo que permite pronosticar las 4 semanas siguientes al cierre.
--
-- Tratamiento de eventos (justificación en el informe):
--   es_feriado         feriados nacionales de Brasil      -> se MODELA
--   black_friday       viernes de Black Friday            -> se MODELA
--   post_black_friday  sábado a martes siguientes (efecto
--                      residual + Cyber Monday)           -> se MODELA
--   fiestas_fin_anio   24-dic a 1-ene                     -> se MODELA
--   paro_camioneros    paro nacional de camioneros
--                      (21 a 31-may-2018), no recurrente  -> se MARCA
--                      (dummy en el ajuste, 0 al pronosticar, y se
--                       excluye de las métricas de validación)
--   partido_brasil     partidos de Brasil en el Mundial
--                      2018 (14-jun a 15-jul)             -> solo DIAGNÓSTICO
--                      (no entra a los modelos: solo hay 2 partidos antes
--                       del período de prueba y las fechas de eliminatorias
--                       no se conocen al momento de pronosticar)
--
-- Parámetros (en este orden):
--   1. fecha_inicio  DATE  primer día del calendario
--   2. fecha_fin     DATE  último día del calendario (incluido)
-- =====================================================================
WITH params AS (
    SELECT
        CAST(? AS DATE) AS fecha_inicio,
        CAST(? AS DATE) AS fecha_fin
),
grilla AS (
    SELECT CAST(g.fecha AS DATE) AS fecha
    FROM params AS p,
         generate_series(
             CAST(p.fecha_inicio AS TIMESTAMP),
             CAST(p.fecha_fin    AS TIMESTAMP),
             INTERVAL 1 DAY
         ) AS g(fecha)
),
-- Feriados nacionales (incluye Carnaval y Viernes Santo, que en la
-- práctica paralizan el comercio aunque Carnaval sea "ponto facultativo")
feriados (fecha, nombre) AS (
    VALUES
        (DATE '2017-01-01', 'Confraternização Universal'),
        (DATE '2017-02-27', 'Carnaval (lunes)'),
        (DATE '2017-02-28', 'Carnaval (martes)'),
        (DATE '2017-04-14', 'Sexta-feira Santa'),
        (DATE '2017-04-21', 'Tiradentes'),
        (DATE '2017-05-01', 'Dia do Trabalho'),
        (DATE '2017-06-15', 'Corpus Christi'),
        (DATE '2017-09-07', 'Independência'),
        (DATE '2017-10-12', 'Nossa Senhora Aparecida'),
        (DATE '2017-11-02', 'Finados'),
        (DATE '2017-11-15', 'Proclamação da República'),
        (DATE '2017-12-25', 'Natal'),
        (DATE '2018-01-01', 'Confraternização Universal'),
        (DATE '2018-02-12', 'Carnaval (lunes)'),
        (DATE '2018-02-13', 'Carnaval (martes)'),
        (DATE '2018-03-30', 'Sexta-feira Santa'),
        (DATE '2018-04-21', 'Tiradentes'),
        (DATE '2018-05-01', 'Dia do Trabalho'),
        (DATE '2018-05-31', 'Corpus Christi'),
        (DATE '2018-09-07', 'Independência'),
        (DATE '2018-10-12', 'Nossa Senhora Aparecida'),
        (DATE '2018-11-02', 'Finados'),
        (DATE '2018-11-15', 'Proclamação da República'),
        (DATE '2018-12-25', 'Natal')
),
-- Black Friday = día siguiente al cuarto jueves de noviembre
black_friday AS (
    SELECT DATE '2016-11-25' AS fecha UNION ALL
    SELECT DATE '2017-11-24'          UNION ALL
    SELECT DATE '2018-11-23'
),
-- Partidos de la selección de Brasil en el Mundial de Rusia 2018
partidos_brasil AS (
    SELECT CAST(d AS DATE) AS fecha
    FROM (VALUES ('2018-06-17'), ('2018-06-22'), ('2018-06-27'),
                 ('2018-07-02'), ('2018-07-06')) AS t(d)
)
SELECT
    g.fecha,
    isodow(g.fecha)                              AS dia_semana,   -- 1 = lunes ... 7 = domingo
    day(g.fecha)                                 AS dia_mes,
    month(g.fecha)                               AS mes,
    CAST(isodow(g.fecha) >= 6 AS INTEGER)        AS fin_de_semana,
    CAST(f.fecha IS NOT NULL AS INTEGER)         AS es_feriado,
    f.nombre                                     AS nombre_feriado,
    CAST(bf.fecha IS NOT NULL AS INTEGER)        AS black_friday,
    CAST(EXISTS (
        SELECT 1 FROM black_friday AS b
        WHERE g.fecha BETWEEN b.fecha + 1 AND b.fecha + 4
    ) AS INTEGER)                                AS post_black_friday,
    CAST(
        (month(g.fecha) = 12 AND day(g.fecha) >= 24)
        OR (month(g.fecha) = 1 AND day(g.fecha) = 1)
    AS INTEGER)                                  AS fiestas_fin_anio,
    CAST(g.fecha BETWEEN DATE '2018-05-21' AND DATE '2018-05-31'
    AS INTEGER)                                  AS paro_camioneros,
    CAST(pb.fecha IS NOT NULL AS INTEGER)        AS partido_brasil
FROM grilla AS g
LEFT JOIN feriados        AS f  ON f.fecha  = g.fecha
LEFT JOIN black_friday    AS bf ON bf.fecha = g.fecha
LEFT JOIN partidos_brasil AS pb ON pb.fecha = g.fecha
ORDER BY g.fecha;
