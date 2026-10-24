-- ============================================================================
-- serie_diaria.sql
-- Propósito:   Serie diaria de órdenes compradas en el período útil, con calendario completo.
-- Operaciones:
--   1. Calcula los límites: el fin es el último DOMINGO <= corte,
--      corte - dayofweek(corte), porque dayofweek vale 0 el domingo.
--   2. Genera todas las fechas entre inicio y fin.
--   3. Cuenta órdenes por día de compra dentro de los límites.
--   4. Une calendario y conteos con LEFT JOIN: un día sin órdenes vale 0.
-- Nota:        terminar en domingo hace que cada origen cierre una semana y que los
--              28 días siguientes sean cuatro semanas lunes-domingo.
-- Parámetros:  1) inicio del período útil; 2) fecha de corte de cobertura.
-- Salida:      una fila por día: fecha, y.
-- ============================================================================
WITH limites AS (
    SELECT inicio, corte - CAST(dayofweek(corte) AS INTEGER) AS fin
    FROM (SELECT CAST(? AS DATE) AS inicio, CAST(? AS DATE) AS corte)
), calendario AS (
    SELECT CAST(unnest(generate_series(inicio, fin, INTERVAL 1 DAY)) AS DATE) AS fecha
    FROM limites
), conteos AS (
    SELECT CAST(order_purchase_timestamp AS DATE) AS fecha, count(*) AS ordenes
    FROM orders, limites
    WHERE order_purchase_timestamp >= inicio
      AND order_purchase_timestamp < fin + INTERVAL 1 DAY
    GROUP BY 1
)
SELECT fecha, coalesce(ordenes, 0)::INTEGER AS y
FROM calendario LEFT JOIN conteos USING(fecha) ORDER BY fecha;
