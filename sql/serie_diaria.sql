-- Parámetros: inicio del período útil y fecha de corte de cobertura.
-- La serie termina en el último DOMINGO <= corte: cada origen cierra una semana
-- completa y los 28 días siguientes forman 4 semanas lunes-domingo.
-- dayofweek: domingo=0 ... sábado=6, así que corte - dayofweek(corte) es ese domingo.
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
