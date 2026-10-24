-- ============================================================================
-- eda_mapa_clientes.sql
-- Propósito:   Clientes reales por prefijo postal con su coordenada central (mapa).
-- Operaciones:
--   1. Promedia latitud y longitud por prefijo ANTES de unir (geolocation tiene varias
--      filas por prefijo) y descarta coordenadas fuera de Brasil.
--   2. Cuenta clientes distintos (customer_unique_id) por prefijo dentro del período útil
--      y toma el estado más frecuente del prefijo.
--   3. Une conteos y centroides por prefijo.
-- Parámetros:  1) inicio del período útil; 2) fin del período útil.
-- Salida:      una fila por prefijo: prefijo, estado, lat, lng, clientes.
-- ============================================================================
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
