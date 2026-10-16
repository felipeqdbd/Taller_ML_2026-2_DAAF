WITH i AS (SELECT order_id,count(*) n FROM order_items GROUP BY 1),
p AS (SELECT order_id,count(*) n FROM order_payments GROUP BY 1),
r AS (SELECT order_id,count(*) n FROM order_reviews GROUP BY 1)
SELECT count(*) ordenes, sum(coalesce(i.n,1)) filas_join_items,
 sum(coalesce(p.n,1)) filas_join_pagos,
 sum(coalesce(i.n,1)*coalesce(p.n,1)) filas_join_items_y_pagos,
 count(*) FILTER(WHERE i.n>1) ordenes_varios_items,
 count(*) FILTER(WHERE p.n>1) ordenes_varios_pagos,
 count(*) FILTER(WHERE r.n>1) ordenes_varias_resenas,
 count(*) FILTER(WHERE c.customer_id IS NULL) sin_cliente
FROM orders o LEFT JOIN i USING(order_id) LEFT JOIN p USING(order_id)
LEFT JOIN r USING(order_id) LEFT JOIN customers c USING(customer_id);