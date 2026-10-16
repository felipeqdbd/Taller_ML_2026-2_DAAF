-- Lo que ve el modelo al cierre del origen sobre un evento de calendario.
SELECT origen,fecha,h,dia_semana,festivo,black_friday,
       post_black_friday,fin_anio,lag_0,media_28,real
FROM variables
WHERE origen=CAST(? AS DATE)
  AND fecha BETWEEN CAST(? AS DATE) AND CAST(? AS DATE)
ORDER BY h;
