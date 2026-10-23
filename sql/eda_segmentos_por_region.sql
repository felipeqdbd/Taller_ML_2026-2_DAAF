-- ============================================================================
-- eda_segmentos_por_region.sql
-- Propósito:   Composición de segmentos de clientes dentro de cada región.
-- Operaciones:
--   1. Agrupa la vista segmentos por región y segmento.
--   2. Calcula clientes, participación del segmento en su región (%) y gasto
--      promedio ponderado por clientes.
-- Parámetros:  ninguno.
-- Requiere:    vista en memoria segmentos (salida de eda_segmentos_region.sql).
-- Salida:      una fila por (región, segmento).
-- ============================================================================
SELECT region,segmento,sum(clientes) AS clientes,
       round(100*sum(clientes)/sum(sum(clientes)) OVER (PARTITION BY region),1) AS pct_region,
       round(sum(gasto_promedio*clientes)/sum(clientes),2) AS gasto_promedio
FROM segmentos GROUP BY 1,2 ORDER BY 1,2;
