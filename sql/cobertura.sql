-- ============================================================================
-- cobertura.sql
-- Propósito:   Cobertura temporal mes a mes, para elegir el período útil.
-- Operaciones:
--   1. Toma el primer y el último mes con compras.
--   2. Genera todos los meses entre ambos, incluidos los meses sin compras.
--   3. Cuenta órdenes, días con compras y primera/última compra de cada mes.
--   4. Une calendario y conteos con LEFT JOIN; un mes sin compras queda en cero.
-- Parámetros:  ninguno.
-- Salida:      una fila por mes.
-- ============================================================================
-- Se incluyen meses sin compras para no ocultar huecos como noviembre de 2016.
WITH limites AS (
 SELECT date_trunc('month',min(order_purchase_timestamp)) inicio,
        date_trunc('month',max(order_purchase_timestamp)) fin FROM orders
), calendario AS (
 SELECT d::DATE mes FROM limites,
 generate_series(inicio,fin,INTERVAL 1 MONTH) t(d)
), conteos AS (
 SELECT date_trunc('month',order_purchase_timestamp)::DATE mes,
 count(*) ordenes,count(DISTINCT order_purchase_timestamp::DATE) dias_con_compras,
 min(order_purchase_timestamp) primera_compra,max(order_purchase_timestamp) ultima_compra
 FROM orders GROUP BY 1
)
SELECT mes,coalesce(ordenes,0) ordenes,coalesce(dias_con_compras,0) dias_con_compras,
 date_diff('day',mes,mes+INTERVAL 1 MONTH) dias_del_mes,
 primera_compra,ultima_compra
FROM calendario LEFT JOIN conteos USING(mes) ORDER BY mes;
