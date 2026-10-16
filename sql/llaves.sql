-- Repetidos en reviews/prefijos requieren interpretar granularidad.
SELECT 'orders' tabla, 'order_id' llave_candidata, count(*) filas, count(DISTINCT order_id) distintos, count(*)-count(DISTINCT order_id) repetidos, count(*) FILTER(WHERE order_id IS NULL) nulos FROM orders
UNION ALL
SELECT 'customers' tabla, 'customer_id' llave_candidata, count(*) filas, count(DISTINCT customer_id) distintos, count(*)-count(DISTINCT customer_id) repetidos, count(*) FILTER(WHERE customer_id IS NULL) nulos FROM customers
UNION ALL
SELECT 'sellers' tabla, 'seller_id' llave_candidata, count(*) filas, count(DISTINCT seller_id) distintos, count(*)-count(DISTINCT seller_id) repetidos, count(*) FILTER(WHERE seller_id IS NULL) nulos FROM sellers
UNION ALL
SELECT 'products' tabla, 'product_id' llave_candidata, count(*) filas, count(DISTINCT product_id) distintos, count(*)-count(DISTINCT product_id) repetidos, count(*) FILTER(WHERE product_id IS NULL) nulos FROM products
UNION ALL
SELECT 'order_items' tabla, 'order_id,order_item_id' llave_candidata, count(*) filas, count(DISTINCT (order_id,order_item_id)) distintos, count(*)-count(DISTINCT (order_id,order_item_id)) repetidos, count(*) FILTER(WHERE order_id IS NULL OR order_item_id IS NULL) nulos FROM order_items
UNION ALL
SELECT 'order_payments' tabla, 'order_id,payment_sequential' llave_candidata, count(*) filas, count(DISTINCT (order_id,payment_sequential)) distintos, count(*)-count(DISTINCT (order_id,payment_sequential)) repetidos, count(*) FILTER(WHERE order_id IS NULL OR payment_sequential IS NULL) nulos FROM order_payments
UNION ALL
SELECT 'order_reviews' tabla, 'review_id' llave_candidata, count(*) filas, count(DISTINCT review_id) distintos, count(*)-count(DISTINCT review_id) repetidos, count(*) FILTER(WHERE review_id IS NULL) nulos FROM order_reviews
UNION ALL
SELECT 'category_translation' tabla, 'product_category_name' llave_candidata, count(*) filas, count(DISTINCT product_category_name) distintos, count(*)-count(DISTINCT product_category_name) repetidos, count(*) FILTER(WHERE product_category_name IS NULL) nulos FROM category_translation
UNION ALL
SELECT 'geolocation' tabla, 'geolocation_zip_code_prefix' llave_candidata, count(*) filas, count(DISTINCT geolocation_zip_code_prefix) distintos, count(*)-count(DISTINCT geolocation_zip_code_prefix) repetidos, count(*) FILTER(WHERE geolocation_zip_code_prefix IS NULL) nulos FROM geolocation;