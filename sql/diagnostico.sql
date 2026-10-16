-- Únicamente el pasado disponible antes de la primera validación.
SELECT fecha,y,
 avg(y) OVER (ORDER BY fecha ROWS BETWEEN 6 PRECEDING AND CURRENT ROW) media_7,
 avg(y) OVER (ORDER BY fecha ROWS BETWEEN 27 PRECEDING AND CURRENT ROW) media_28
FROM serie WHERE fecha<=CAST(? AS DATE) ORDER BY fecha;
