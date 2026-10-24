-- ============================================================================
-- eda_entregas.sql
-- Propósito:   Resumen de tiempos de entrega y retrasos.
-- Operaciones:
--   1. Filtra órdenes entregadas (delivered) con fecha de entrega registrada.
--   2. Calcula media, mediana y percentil 90 de los días entre compra y entrega.
--   3. Calcula la proporción entregada después de la fecha estimada (por día calendario)
--      y el retraso medio en días.
-- Parámetros:  ninguno.
-- Salida:      una fila con las métricas de entrega.
-- ============================================================================
SELECT count(*) observaciones,
 avg(date_diff('day',order_purchase_timestamp,order_delivered_customer_date)) media_dias_entrega,
 median(date_diff('day',order_purchase_timestamp,order_delivered_customer_date)) mediana_dias_entrega,
 quantile_cont(date_diff('day',order_purchase_timestamp,order_delivered_customer_date),0.9) p90_dias_entrega,
 avg(CAST(order_delivered_customer_date::DATE>order_estimated_delivery_date::DATE AS INTEGER)) proporcion_tarde,
 avg(date_diff('day',order_estimated_delivery_date::DATE,order_delivered_customer_date::DATE)) retraso_medio_dias
FROM orders WHERE order_status='delivered' AND order_delivered_customer_date IS NOT NULL;