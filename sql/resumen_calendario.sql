-- Los indicadores pueden coincidir: Navidad es festivo y fin de año.
SELECT year(fecha) AS anio,count(*) AS dias_calendario,
       sum(festivo) AS dias_festivos_nacionales,
       sum(black_friday) AS dias_black_friday,
       sum(post_black_friday) AS dias_post_black_friday,
       sum(fin_anio) AS dias_fin_anio
FROM calendario GROUP BY 1 ORDER BY 1;
