WITH frecuencia AS (
 SELECT customer_unique_id,count(DISTINCT order_id) compras FROM customers JOIN orders USING(customer_id) GROUP BY 1)
SELECT compras,count(*) clientes FROM frecuencia GROUP BY 1 ORDER BY 1;