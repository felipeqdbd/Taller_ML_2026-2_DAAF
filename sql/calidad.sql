WITH items AS (
 SELECT order_id, sum(price+freight_value) AS total FROM order_items GROUP BY 1
), pagos AS (
 SELECT order_id, sum(payment_value) AS total FROM order_payments GROUP BY 1
)
SELECT count(*) AS ordenes,
 count(*)-count(DISTINCT o.order_id) AS ids_duplicados,
 count(*) FILTER(WHERE order_purchase_timestamp IS NULL) AS compras_sin_fecha,
 count(*) FILTER(WHERE order_delivered_customer_date < order_purchase_timestamp) AS entrega_antes_compra,
 count(*) FILTER(WHERE order_approved_at < order_purchase_timestamp) AS aprobacion_antes_compra,
 count(*) FILTER(WHERE i.order_id IS NULL) AS sin_items,
 count(*) FILTER(WHERE p.order_id IS NULL) AS sin_pagos,
 count(*) FILTER(WHERE abs(i.total-p.total)>0.02) AS diferencia_pago_mayor_2_centavos
FROM orders o LEFT JOIN items i USING(order_id) LEFT JOIN pagos p USING(order_id);
