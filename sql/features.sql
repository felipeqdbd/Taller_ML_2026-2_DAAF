-- Las ventanas se calculan ANTES del cruce con los 28 horizontes.
-- lag_0 es el conteo del origen, que ya se conoce al cierre del día.
-- Los 91 días completos dan la misma muestra a las cuatro variantes ML.
WITH historia AS (
 SELECT fecha AS origen, y AS lag_0,
 lag(y,1) OVER w lag_1, lag(y,2) OVER w lag_2, lag(y,3) OVER w lag_3,
 lag(y,4) OVER w lag_4, lag(y,5) OVER w lag_5, lag(y,6) OVER w lag_6,
 lag(y,13) OVER w lag_13, lag(y,27) OVER w lag_27,
 avg(y) OVER (ORDER BY fecha ROWS BETWEEN 6 PRECEDING AND CURRENT ROW) media_7,
 avg(y) OVER (ORDER BY fecha ROWS BETWEEN 27 PRECEDING AND CURRENT ROW) media_28,
 avg(y) OVER (ORDER BY fecha ROWS BETWEEN 90 PRECEDING AND CURRENT ROW) media_91,
 stddev_samp(y) OVER (ORDER BY fecha ROWS BETWEEN 27 PRECEDING AND CURRENT ROW) sd_28,
 count(*) OVER (ORDER BY fecha ROWS BETWEEN 90 PRECEDING AND CURRENT ROW) n_historia
 FROM serie WINDOW w AS (ORDER BY fecha)
), pares AS (
 SELECT *, (origen+h*INTERVAL 1 DAY)::DATE fecha,
 -- Desplazamiento hasta el último día observado del mismo día de semana.
 ((7-(h%7))%7)::INTEGER desplazamiento
 FROM historia CROSS JOIN range(1,29) t(h) WHERE n_historia=91
)
SELECT p.*, c.dia_semana,c.dia_mes,c.mes,c.festivo,c.black_friday,
 c.post_black_friday,c.fin_anio,
 date_diff('day',CAST(? AS DATE),p.fecha) tendencia,
 s.y AS real,
 p.media_7/(1+p.media_28) AS razon_7_28,
 p.media_28/(1+p.media_91) AS razon_28_91,
 p.sd_28/(1+p.media_28) AS cv_28,
 sem.ultimo_mismo_dia, sem.media_4_mismo_dia,
 ln(1+p.lag_0)-ln(1+p.media_28) AS rel_lag_0,
 ln(1+p.lag_1)-ln(1+p.media_28) AS rel_lag_1,
 ln(1+p.lag_2)-ln(1+p.media_28) AS rel_lag_2,
 ln(1+p.lag_3)-ln(1+p.media_28) AS rel_lag_3,
 ln(1+p.lag_4)-ln(1+p.media_28) AS rel_lag_4,
 ln(1+p.lag_5)-ln(1+p.media_28) AS rel_lag_5,
 ln(1+p.lag_6)-ln(1+p.media_28) AS rel_lag_6,
 ln(1+sem.ultimo_mismo_dia)-ln(1+p.media_28) AS rel_mismo_dia,
 ln(1+sem.media_4_mismo_dia)-ln(1+p.media_28) AS rel_media_4_dias
FROM pares p JOIN calendario c ON c.fecha=p.fecha
LEFT JOIN serie s ON s.fecha=p.fecha
LEFT JOIN LATERAL (
 SELECT max(y) FILTER(WHERE z.fecha=p.origen-p.desplazamiento*INTERVAL 1 DAY) ultimo_mismo_dia,
 avg(y) media_4_mismo_dia
 FROM serie z WHERE z.fecha IN (
 p.origen-p.desplazamiento*INTERVAL 1 DAY,
 p.origen-(p.desplazamiento+7)*INTERVAL 1 DAY,
 p.origen-(p.desplazamiento+14)*INTERVAL 1 DAY,
 p.origen-(p.desplazamiento+21)*INTERVAL 1 DAY)
) sem ON TRUE
ORDER BY p.origen,p.h;
