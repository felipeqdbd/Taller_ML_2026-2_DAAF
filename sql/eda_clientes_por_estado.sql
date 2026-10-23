-- ============================================================================
-- eda_clientes_por_estado.sql
-- Propósito:   Clientes únicos, recurrencia, gasto alto y gasto promedio por estado.
-- Operaciones:
--   1. Agrupa la vista segmentos por estado.
--   2. Calcula clientes, % de recurrentes, % de única compra con gasto alto y
--      gasto promedio ponderado por clientes.
-- Parámetros:  ninguno.
-- Requiere:    vista en memoria segmentos (salida de eda_segmentos_region.sql).
-- Salida:      una fila por estado, de mayor a menor número de clientes.
-- ============================================================================
SELECT estado,any_value(region) AS region,sum(clientes) AS clientes,
       round(100*coalesce(sum(clientes) FILTER (WHERE segmento='Recurrente'),0)/sum(clientes),2) AS pct_recurrentes,
       round(100*coalesce(sum(clientes) FILTER (WHERE segmento='Única compra · gasto alto'),0)/sum(clientes),1) AS pct_gasto_alto,
       round(sum(gasto_promedio*clientes)/sum(clientes),2) AS gasto_promedio
FROM segmentos GROUP BY 1 ORDER BY clientes DESC;
