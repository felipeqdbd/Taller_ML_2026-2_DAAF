-- Casos didácticos: un 1 significa que se conoce ese atributo del día.
-- La columna observada se muestra para interpretar, nunca entra al calendario.
SELECT c.fecha,c.dia_semana,c.festivo,c.black_friday,
       c.post_black_friday,c.fin_anio,s.y AS pedidos_observados
FROM calendario c LEFT JOIN serie s USING(fecha)
WHERE c.fecha IN (
 DATE '2017-11-24', DATE '2017-11-25', DATE '2017-12-24',
 DATE '2017-12-25', DATE '2018-01-01', DATE '2018-05-21', DATE '2018-09-07'
)
ORDER BY c.fecha;
