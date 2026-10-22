-- Clientes reales por prefijo postal con su coordenada central, para dibujar el mapa.
-- Parámetros: inicio y fin del período útil.
-- geolocation tiene varias filas por prefijo: se promedia por prefijo ANTES de unir
-- y se descartan coordenadas fuera de Brasil (errores de captura de la fuente).
WITH centroides AS (
    SELECT geolocation_zip_code_prefix AS prefijo,
           avg(geolocation_lat) AS lat, avg(geolocation_lng) AS lng
    FROM geolocation
    WHERE geolocation_lat BETWEEN -34 AND 5.5
      AND geolocation_lng BETWEEN -74 AND -34
    GROUP BY 1
), clientes AS (
    SELECT c.customer_zip_code_prefix AS prefijo,
           mode(c.customer_state) AS estado,
           count(DISTINCT c.customer_unique_id) AS clientes
    FROM orders o
    JOIN customers c USING (customer_id)
    WHERE o.order_purchase_timestamp >= CAST(? AS DATE)
      AND o.order_purchase_timestamp < CAST(? AS DATE) + INTERVAL 1 DAY
    GROUP BY 1
)
SELECT prefijo, estado, lat, lng, clientes
FROM clientes JOIN centroides USING (prefijo)
ORDER BY clientes;
