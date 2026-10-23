-- ============================================================================
-- tablas.sql
-- Propósito:   Tamaño de cada tabla de olist.duckdb para describir el modelo relacional.
-- Operaciones:
--   1. Cuenta las filas de cada una de las nueve tablas del dataset.
--   2. Las une en una sola salida con el nombre de la tabla.
-- Parámetros:  ninguno.
-- Salida:      una fila por tabla: tabla, filas.
-- ============================================================================
SELECT 'orders' AS tabla,count(*) AS filas FROM orders
UNION ALL SELECT 'customers',count(*) FROM customers
UNION ALL SELECT 'order_items',count(*) FROM order_items
UNION ALL SELECT 'order_payments',count(*) FROM order_payments
UNION ALL SELECT 'order_reviews',count(*) FROM order_reviews
UNION ALL SELECT 'products',count(*) FROM products
UNION ALL SELECT 'sellers',count(*) FROM sellers
UNION ALL SELECT 'category_translation',count(*) FROM category_translation
UNION ALL SELECT 'geolocation',count(*) FROM geolocation;
