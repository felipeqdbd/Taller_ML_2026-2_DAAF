SELECT CAST(order_purchase_timestamp AS DATE) fecha,count(*) ordenes
FROM orders WHERE order_purchase_timestamp>=CAST(? AS DATE) GROUP BY 1 ORDER BY 1;