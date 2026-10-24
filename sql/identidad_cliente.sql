-- ============================================================================
-- identidad_cliente.sql
-- Propósito:   Comparar customer_id y customer_unique_id como identificadores de cliente.
-- Operaciones:
--   1. Cuenta registros de customers, customer_id distintos y personas distintas
--      (customer_unique_id).
--   2. Comprueba la relación customer_id - orders: cuántos customer_id aparecen en más
--      de una orden.
--   3. Agrega por customer_unique_id: número de customer_id, de estados y de prefijos
--      postales distintos de cada persona.
--   4. Resume cuántas personas tienen varios customer_id (es decir, varias compras),
--      el máximo por persona y qué parte de las órdenes hacen esas personas.
-- Parámetros:  ninguno.
-- Salida:      una fila con los conteos de identidad.
-- ============================================================================
WITH por_id AS (
    SELECT customer_id, count(*) AS ordenes FROM orders GROUP BY 1
), por_persona AS (
    SELECT customer_unique_id,
           count(DISTINCT customer_id) AS ids,
           count(DISTINCT customer_state) AS estados,
           count(DISTINCT customer_zip_code_prefix) AS prefijos
    FROM customers GROUP BY 1
)
SELECT
    (SELECT count(*) FROM customers) AS registros_customers,
    (SELECT count(DISTINCT customer_id) FROM customers) AS customer_id_distintos,
    (SELECT count(*) FROM por_id WHERE ordenes > 1) AS customer_id_con_varias_ordenes,
    count(*) AS personas_customer_unique_id,
    count(*) FILTER (WHERE ids > 1) AS personas_con_varios_customer_id,
    max(ids) AS max_customer_id_por_persona,
    sum(ids) FILTER (WHERE ids > 1) AS ordenes_de_personas_recurrentes,
    count(*) FILTER (WHERE estados > 1) AS personas_en_varios_estados,
    count(*) FILTER (WHERE prefijos > 1) AS personas_en_varios_prefijos
FROM por_persona;
