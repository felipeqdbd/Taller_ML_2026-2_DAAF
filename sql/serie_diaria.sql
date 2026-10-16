-- Los límites son parámetros: el notebook no interpola fechas en SQL.
WITH calendario AS (
    SELECT CAST(d AS DATE) AS fecha
    FROM generate_series(CAST(? AS DATE), CAST(? AS DATE), INTERVAL 1 DAY) t(d)
), conteos AS (
    SELECT CAST(order_purchase_timestamp AS DATE) AS fecha, count(*) AS ordenes
    FROM orders
    WHERE order_purchase_timestamp >= CAST(? AS DATE)
      AND order_purchase_timestamp < CAST(? AS DATE) + INTERVAL 1 DAY
    GROUP BY 1
)
SELECT fecha, coalesce(ordenes, 0)::INTEGER AS y
FROM calendario LEFT JOIN conteos USING(fecha) ORDER BY fecha;
