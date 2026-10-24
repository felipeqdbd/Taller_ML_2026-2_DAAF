-- ============================================================================
-- calidad_extra.sql
-- Propósito:   Faltantes y relaciones huérfanas entre tablas.
-- Operaciones:
--   1. Cada columna es una subconsulta escalar independiente.
--   2. Cuenta nulos de aprobación, entrega y categoría; productos sin traducción (LEFT JOIN);
--      clientes y vendedores cuyo prefijo postal no existe en geolocation (NOT EXISTS);
--      e ítems sin orden, sin producto o sin vendedor.
-- Parámetros:  ninguno.
-- Salida:      una fila con un conteo por problema.
-- ============================================================================
SELECT
 (SELECT count(*) FROM orders WHERE order_approved_at IS NULL) aprobacion_nula,
 (SELECT count(*) FROM orders WHERE order_delivered_customer_date IS NULL) entrega_nula,
 (SELECT count(*) FROM products WHERE product_category_name IS NULL) categoria_nula,
 (SELECT count(*) FROM products p LEFT JOIN category_translation t USING(product_category_name)
  WHERE p.product_category_name IS NOT NULL AND t.product_category_name IS NULL) productos_sin_traduccion,
 (SELECT count(*) FROM customers c WHERE NOT EXISTS
  (SELECT 1 FROM geolocation g WHERE g.geolocation_zip_code_prefix=c.customer_zip_code_prefix)) clientes_sin_geolocalizacion,
 (SELECT count(*) FROM sellers s WHERE NOT EXISTS
  (SELECT 1 FROM geolocation g WHERE g.geolocation_zip_code_prefix=s.seller_zip_code_prefix)) vendedores_sin_geolocalizacion,
 (SELECT count(*) FROM order_items i WHERE NOT EXISTS
  (SELECT 1 FROM orders o WHERE o.order_id=i.order_id)) items_huerfanos,
 (SELECT count(*) FROM order_items i WHERE NOT EXISTS
  (SELECT 1 FROM products p WHERE p.product_id=i.product_id)) items_sin_producto,
 (SELECT count(*) FROM order_items i WHERE NOT EXISTS
  (SELECT 1 FROM sellers s WHERE s.seller_id=i.seller_id)) items_sin_vendedor;