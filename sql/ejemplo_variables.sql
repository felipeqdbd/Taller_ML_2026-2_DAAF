-- ============================================================================
-- ejemplo_variables.sql
-- Propósito:   Variables de un origen para tres horizontes, como ejemplo didáctico.
-- Operaciones:
--   1. Filtra la vista variables por un origen y los horizontes 1, 7 y 28.
-- Parámetros:  1) fecha de origen.
-- Requiere:    vista en memoria variables (salida de features.sql).
-- Salida:      una fila por horizonte; real es la etiqueta, nunca una variable.
-- ============================================================================
SELECT origen,fecha,h,lag_0,media_7,media_28,media_91,
       ultimo_mismo_dia,media_4_mismo_dia,real
FROM variables
WHERE origen=CAST(? AS DATE) AND h IN (1,7,28) ORDER BY h;
