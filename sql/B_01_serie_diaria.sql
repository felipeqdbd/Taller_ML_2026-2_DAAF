-- =====================================================================
-- Módulo B · Consulta 1: serie diaria de órdenes
-- ---------------------------------------------------------------------
-- Una fila por día calendario entre fecha_inicio y fecha_fin (ambas
-- incluidas), con el número de órdenes compradas ese día según
-- order_purchase_timestamp. Los días sin órdenes aparecen con 0 gracias
-- a la grilla de fechas (generate_series) unida con LEFT JOIN.
--
-- Decisiones:
--   * Se cuentan TODAS las órdenes, sin filtrar order_status: para planear
--     capacidad importa la demanda recibida, no si la orden se entregó.
--     (canceled + unavailable son ~1.2 % del total).
--   * orders -> customers es 1:1 por customer_id, así que el JOIN no
--     duplica filas (verificado en el Módulo 0). El JOIN solo se usa para
--     el filtro opcional por estado del cliente (extensión São Paulo).
--   * El día se toma de la marca de tiempo local tal como viene en la
--     base (CAST a DATE), sin conversión de zona horaria.
--
-- Parámetros (en este orden):
--   1. fecha_inicio  DATE     primer día de la serie
--   2. fecha_fin     DATE     último día de la serie (incluido)
--   3. estado        VARCHAR  sigla de customer_state (p. ej. 'SP');
--                             NULL = todo Brasil
-- =====================================================================
WITH params AS (
    SELECT
        CAST(? AS DATE)    AS fecha_inicio,
        CAST(? AS DATE)    AS fecha_fin,
        CAST(? AS VARCHAR) AS estado
),
-- Grilla completa de días: garantiza que los días sin órdenes existan
grilla AS (
    SELECT CAST(g.fecha AS DATE) AS fecha
    FROM params AS p,
         generate_series(
             CAST(p.fecha_inicio AS TIMESTAMP),
             CAST(p.fecha_fin    AS TIMESTAMP),
             INTERVAL 1 DAY
         ) AS g(fecha)
),
conteos AS (
    SELECT
        CAST(o.order_purchase_timestamp AS DATE) AS fecha,
        COUNT(*)                                 AS n_ordenes
    FROM orders AS o
    JOIN customers AS c USING (customer_id)
    CROSS JOIN params AS p
    WHERE o.order_purchase_timestamp >= p.fecha_inicio
      AND o.order_purchase_timestamp <  p.fecha_fin + INTERVAL 1 DAY
      AND (p.estado IS NULL OR c.customer_state = p.estado)
    GROUP BY 1
)
SELECT
    g.fecha,
    COALESCE(c.n_ordenes, 0) AS n_ordenes
FROM grilla AS g
LEFT JOIN conteos AS c USING (fecha)
ORDER BY g.fecha;
