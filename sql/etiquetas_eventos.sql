-- ============================================================================
-- etiquetas_eventos.sql
-- Propósito:   Una fila por fecha y evento: une los indicadores del calendario con los
--              episodios históricos que el calendario no incluye.
-- Operaciones:
--   1. Convierte cada indicador 0/1 de la vista calendario en una fila (fecha, evento).
--   2. Expande cada episodio (desde-hasta) a una fila por día.
--   3. Conserva si la fecha del evento se conocía antes de que ocurriera (previsible).
-- Parámetros:  ninguno.
-- Requiere:    vistas en memoria calendario y episodios (con.register).
-- Salida:      una fila por (fecha, evento); una fecha puede tener varios eventos.
-- ============================================================================
-- Navidad aparece dos veces (festivo y fin_anio): cada indicador se describe por separado.
SELECT fecha,'festivo' AS evento,TRUE AS previsible FROM calendario WHERE festivo=1
UNION ALL SELECT fecha,'carnaval',TRUE FROM calendario WHERE carnaval=1
UNION ALL SELECT fecha,'black_friday',TRUE FROM calendario WHERE black_friday=1
UNION ALL SELECT fecha,'post_black_friday',TRUE FROM calendario WHERE post_black_friday=1
UNION ALL SELECT fecha,'fin_anio',TRUE FROM calendario WHERE fin_anio=1
UNION ALL
SELECT CAST(unnest(generate_series(CAST(desde AS DATE),CAST(hasta AS DATE),INTERVAL 1 DAY)) AS DATE),
       evento,previsible
FROM episodios
ORDER BY 1,2;
