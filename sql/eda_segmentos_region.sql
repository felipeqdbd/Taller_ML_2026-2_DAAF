-- Clientes reales (customer_unique_id) por estado, región y segmento descriptivo.
-- Parámetros: inicio y fin del período útil (los mismos de la serie diaria).
-- Pagos se agregan por orden ANTES de unir: order_payments es 1:N y duplicaría órdenes.
WITH regiones(estado, region) AS (VALUES
    ('AC','Norte'),('AP','Norte'),('AM','Norte'),('PA','Norte'),('RO','Norte'),('RR','Norte'),('TO','Norte'),
    ('AL','Nordeste'),('BA','Nordeste'),('CE','Nordeste'),('MA','Nordeste'),('PB','Nordeste'),
    ('PE','Nordeste'),('PI','Nordeste'),('RN','Nordeste'),('SE','Nordeste'),
    ('DF','Centro-Oeste'),('GO','Centro-Oeste'),('MT','Centro-Oeste'),('MS','Centro-Oeste'),
    ('ES','Sudeste'),('MG','Sudeste'),('RJ','Sudeste'),('SP','Sudeste'),
    ('PR','Sul'),('RS','Sul'),('SC','Sul')
), pagos AS (
    SELECT order_id, sum(payment_value) AS valor FROM order_payments GROUP BY 1
), compras AS (
    SELECT c.customer_unique_id, c.customer_state AS estado,
           o.order_purchase_timestamp AS momento, coalesce(p.valor, 0) AS valor
    FROM orders o
    JOIN customers c USING (customer_id)
    LEFT JOIN pagos p USING (order_id)
    WHERE o.order_purchase_timestamp >= CAST(? AS DATE)
      AND o.order_purchase_timestamp < CAST(? AS DATE) + INTERVAL 1 DAY
), por_cliente AS (
    -- Si un cliente compró desde varios estados, se usa el de su compra más reciente.
    SELECT customer_unique_id, arg_max(estado, momento) AS estado,
           count(*) AS compras, sum(valor) AS gasto
    FROM compras GROUP BY 1
), umbral AS (
    SELECT quantile_cont(gasto, 0.75) AS p75 FROM por_cliente
), segmentos AS (
    SELECT estado, compras, gasto,
           CASE WHEN compras >= 2 THEN 'Recurrente'
                WHEN gasto >= p75 THEN 'Única compra · gasto alto'
                ELSE 'Única compra · gasto bajo-medio' END AS segmento
    FROM por_cliente, umbral
)
SELECT r.region, s.estado, s.segmento,
       count(*) AS clientes,
       sum(s.compras) AS ordenes,
       round(avg(s.gasto), 2) AS gasto_promedio
FROM segmentos s JOIN regiones r USING (estado)
GROUP BY 1, 2, 3
ORDER BY 1, 2, 3;
