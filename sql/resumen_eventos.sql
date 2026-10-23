-- ============================================================================
-- resumen_eventos.sql
-- Propósito:   Magnitud observada de cada tipo de evento frente a lo esperado.
-- Operaciones:
--   1. Une cada etiqueta de evento con el valor observado y esperado del día.
--   2. Agrupa por evento: días, primera y última fecha, totales y razones.
-- Parámetros:  ninguno.
-- Requiere:    vistas en memoria etiquetas y esperados (esperado_mismo_dia.sql).
-- Salida:      una fila por evento con días dentro de la ventana analizada.
-- ============================================================================
-- Descripción histórica: una razón no es un efecto causal estimado.
SELECT e.evento,bool_and(e.previsible) AS previsible,count(*) AS dias,
       min(e.fecha) AS desde,max(e.fecha) AS hasta,
       sum(x.y) AS observado,round(sum(x.esperado)) AS esperado,
       sum(x.y)/sum(x.esperado) AS razon_total,
       min(x.razon) AS razon_min,max(x.razon) AS razon_max
FROM etiquetas e JOIN esperados x USING(fecha)
GROUP BY e.evento ORDER BY razon_total DESC;
