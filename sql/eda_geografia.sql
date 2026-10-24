-- ============================================================================
-- eda_geografia.sql
-- Propósito:   Registros de clientes y vendedores por estado.
-- Operaciones:
--   1. Cuenta customers por customer_state y sellers por seller_state.
--   2. Une ambas poblaciones con UNION ALL.
--   3. Ojo: customers tiene un registro por orden (customer_id), no por persona.
-- Parámetros:  ninguno.
-- Salida:      una fila por población y estado: poblacion, estado, registros.
-- ============================================================================
SELECT 'clientes' poblacion,customer_state estado,count(*) registros FROM customers GROUP BY 2
UNION ALL SELECT 'vendedores',seller_state,count(*) FROM sellers GROUP BY 2 ORDER BY 1,3 DESC;