-- Las distribuciones se calculan por día calendario y solo para entregadas.
WITH base AS (
 SELECT date_diff('day',order_purchase_timestamp::DATE,order_delivered_customer_date::DATE) entrega,
 date_diff('day',order_estimated_delivery_date::DATE,order_delivered_customer_date::DATE) retraso
 FROM orders WHERE order_status='delivered' AND order_delivered_customer_date IS NOT NULL
), grupos AS (
 SELECT 'Entrega' tipo,
 CASE WHEN entrega<=2 THEN 1 WHEN entrega<=7 THEN 2 WHEN entrega<=14 THEN 3
 WHEN entrega<=21 THEN 4 WHEN entrega<=30 THEN 5 ELSE 6 END grupo,
 CASE WHEN entrega<=2 THEN '0-2 días' WHEN entrega<=7 THEN '3-7 días' WHEN entrega<=14 THEN '8-14 días'
 WHEN entrega<=21 THEN '15-21 días' WHEN entrega<=30 THEN '22-30 días' ELSE 'Más de 30 días' END intervalo FROM base
 UNION ALL
 SELECT 'Retraso',
 CASE WHEN retraso<=0 THEN 1 WHEN retraso<=3 THEN 2 WHEN retraso<=7 THEN 3 WHEN retraso<=14 THEN 4 ELSE 5 END,
 CASE WHEN retraso<=0 THEN 'A tiempo/antes' WHEN retraso<=3 THEN '1-3 días tarde'
 WHEN retraso<=7 THEN '4-7 días tarde' WHEN retraso<=14 THEN '8-14 días tarde' ELSE 'Más de 14 días tarde' END FROM base
)
SELECT tipo,grupo,intervalo,count(*) ordenes FROM grupos GROUP BY 1,2,3 ORDER BY 1,2;
