SELECT isodow(fecha) dia_semana, count(*) dias, avg(y) media, median(y) mediana
FROM serie WHERE fecha<=CAST(? AS DATE) GROUP BY 1 ORDER BY 1;
