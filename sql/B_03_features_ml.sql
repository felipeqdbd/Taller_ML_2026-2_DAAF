-- =====================================================================
-- Módulo B · Consulta 3: tabla de entrenamiento del modelo de ML
--                         (estrategia multi-paso DIRECTA)
-- ---------------------------------------------------------------------
-- Una fila por (fecha_origen, horizonte h = 1..28). La fila responde:
-- "con lo observado hasta el cierre de fecha_origen, ¿cuántas órdenes
-- habrá en fecha_origen + h?".
--
-- Por qué no hay fuga de información:
--   * Todas las variables de rezago y medias móviles se calculan con
--     ventanas ROWS ... PRECEDING AND CURRENT ROW sobre fecha_origen:
--     solo usan días <= fecha_origen.
--   * Del día objetivo solo se usan variables de CALENDARIO (día de la
--     semana, feriados, eventos), que se conocen de antemano.
--   * El "último mismo día de la semana" se busca en
--     fecha_objetivo - 7 * ceil(h / 7), que siempre es <= fecha_origen.
--   * En el notebook, para un origen de validación O, solo se entrena
--     con filas cuya fecha_objetivo <= O (el objetivo ya se observó).
--
-- Por qué variables relativas (log-razones respecto a media_28):
--   los árboles no extrapolan niveles. Expresar el objetivo y los
--   rezagos como log(1+y) - log(1+media_28) vuelve la serie
--   aproximadamente estacionaria en nivel y deja al modelo aprender
--   solo la forma (día de la semana, eventos, momentum).
--
-- Requiere las tablas temporales (creadas en el notebook a partir de
-- B_01 y B_02, sin modificar olist.duckdb):
--   serie_b(fecha, n_ordenes)          período observado
--   calendario_b(fecha, dia_semana, ...)  observado + 28 días futuros
-- Sin parámetros: las fechas de corte ya vienen en las tablas temporales.
-- =====================================================================
WITH base AS (
    SELECT
        s.fecha,
        s.n_ordenes,
        c.dia_semana,
        -- día atípico (no representa la demanda "normal")
        CAST(c.black_friday + c.post_black_friday + c.fiestas_fin_anio
             + c.paro_camioneros > 0 AS INTEGER) AS atipico
    FROM serie_b AS s
    JOIN calendario_b AS c USING (fecha)
),
-- Variables disponibles al cierre de cada fecha de origen
origen AS (
    SELECT
        fecha                                       AS fecha_origen,
        n_ordenes                                   AS lag_0,
        LAG(n_ordenes, 1) OVER w                    AS lag_1,
        LAG(n_ordenes, 2) OVER w                    AS lag_2,
        LAG(n_ordenes, 3) OVER w                    AS lag_3,
        LAG(n_ordenes, 4) OVER w                    AS lag_4,
        LAG(n_ordenes, 5) OVER w                    AS lag_5,
        LAG(n_ordenes, 6) OVER w                    AS lag_6,
        AVG(n_ordenes) OVER (w ROWS BETWEEN  6 PRECEDING AND CURRENT ROW) AS media_7,
        AVG(n_ordenes) OVER (w ROWS BETWEEN 27 PRECEDING AND CURRENT ROW) AS media_28,
        AVG(n_ordenes) OVER (w ROWS BETWEEN 90 PRECEDING AND CURRENT ROW) AS media_91,
        STDDEV_SAMP(n_ordenes)
                       OVER (w ROWS BETWEEN 27 PRECEDING AND CURRENT ROW) AS std_28,
        SUM(atipico)   OVER (w ROWS BETWEEN 27 PRECEDING AND CURRENT ROW) AS n_atipicos_28,
        COUNT(*)       OVER (w ROWS BETWEEN 90 PRECEDING AND CURRENT ROW) AS n_obs_91
    FROM base
    WINDOW w AS (ORDER BY fecha)
),
-- Media de los últimos 4 valores del mismo día de la semana (hasta cada fecha)
mismo_dia AS (
    SELECT
        fecha,
        n_ordenes,
        AVG(n_ordenes) OVER (
            PARTITION BY dia_semana ORDER BY fecha
            ROWS BETWEEN 3 PRECEDING AND CURRENT ROW
        ) AS media_mismo_dia_4s
    FROM base
),
horizontes AS (
    SELECT CAST(range AS INTEGER) AS h FROM range(1, 29)
),
filas AS (
    SELECT
        o.*,
        hz.h,
        o.fecha_origen + hz.h                                        AS fecha_objetivo,
        o.fecha_origen + hz.h - 7 * CAST(ceil(hz.h / 7.0) AS INTEGER) AS fecha_ref_semana
    FROM origen AS o
    CROSS JOIN horizontes AS hz
    WHERE o.n_obs_91 = 91              -- solo orígenes con ventanas completas
)
SELECT
    f.fecha_origen,
    f.h                                                    AS horizonte,
    f.fecha_objetivo,
    -- objetivo (NULL si la fecha objetivo está fuera del período observado)
    y.n_ordenes                                            AS y_objetivo,
    ln(1 + y.n_ordenes) - ln(1 + f.media_28)               AS objetivo_rel,
    -- nivel de referencia para deshacer la transformación
    f.media_28,
    -- calendario de la fecha objetivo (conocido de antemano)
    c.dia_semana,
    c.dia_mes,
    c.es_feriado,
    c.black_friday,
    c.post_black_friday,
    c.fiestas_fin_anio,
    c.paro_camioneros,
    -- rezagos relativos al nivel reciente (log-razones)
    ln(1 + f.lag_0) - ln(1 + f.media_28)                   AS r_lag_0,
    ln(1 + f.lag_1) - ln(1 + f.media_28)                   AS r_lag_1,
    ln(1 + f.lag_2) - ln(1 + f.media_28)                   AS r_lag_2,
    ln(1 + f.lag_3) - ln(1 + f.media_28)                   AS r_lag_3,
    ln(1 + f.lag_4) - ln(1 + f.media_28)                   AS r_lag_4,
    ln(1 + f.lag_5) - ln(1 + f.media_28)                   AS r_lag_5,
    ln(1 + f.lag_6) - ln(1 + f.media_28)                   AS r_lag_6,
    -- medias móviles: momentum de corto plazo y tendencia
    ln(1 + f.media_7)  - ln(1 + f.media_28)                AS r_media_7,
    ln(1 + f.media_28) - ln(1 + f.media_91)                AS r_tendencia_28_91,
    f.std_28 / NULLIF(f.media_28, 0)                       AS cv_28,
    f.n_atipicos_28,
    -- estacionalidad semanal observada para el día de la semana objetivo
    ln(1 + m.n_ordenes)          - ln(1 + f.media_28)      AS r_ult_mismo_dia,
    ln(1 + m.media_mismo_dia_4s) - ln(1 + f.media_28)      AS r_mismo_dia_4s
FROM filas AS f
JOIN calendario_b AS c ON c.fecha = f.fecha_objetivo
JOIN mismo_dia    AS m ON m.fecha = f.fecha_ref_semana
LEFT JOIN base    AS y ON y.fecha = f.fecha_objetivo
ORDER BY f.fecha_origen, f.h;
