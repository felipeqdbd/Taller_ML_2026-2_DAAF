SELECT 'clientes' poblacion,customer_state estado,count(*) registros FROM customers GROUP BY 2
UNION ALL SELECT 'vendedores',seller_state,count(*) FROM sellers GROUP BY 2 ORDER BY 1,3 DESC;