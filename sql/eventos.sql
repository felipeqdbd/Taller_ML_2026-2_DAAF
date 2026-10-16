-- Descripción posterior de sucesos; no se interpreta como efecto causal.
SELECT CASE WHEN fecha BETWEEN DATE '2017-11-24' AND DATE '2017-11-28' THEN 'Black Friday y cuatro días siguientes'
 WHEN fecha BETWEEN DATE '2018-05-21' AND DATE '2018-05-31' THEN 'Huelga: ventana de análisis'
 ELSE 'Resto del período' END periodo,
 count(*) dias,sum(y) pedidos,avg(y) media,min(y) minimo,max(y) maximo
FROM serie GROUP BY 1 ORDER BY 1;
