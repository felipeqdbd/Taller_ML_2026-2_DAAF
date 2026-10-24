-- ============================================================================
-- resumen_cola.sql
-- Propósito:   Cuánta actividad queda en la base después del corte de cobertura.
-- Operaciones:
--   1. Filtra la vista cola a los días posteriores al corte.
--   2. Cuenta días, suma órdenes y toma la última fecha con registros.
-- Parámetros:  1) fecha de corte de cobertura.
-- Requiere:    vista en memoria cola (salida de cola.sql).
-- Salida:      una fila: dias, ordenes, ultima_fecha.
-- ============================================================================
SELECT count(*) AS dias,sum(ordenes) AS ordenes,max(fecha) AS ultima_fecha
FROM cola WHERE fecha>CAST(? AS DATE);
