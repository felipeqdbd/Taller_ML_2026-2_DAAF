-- Calendario conocido sin observar ventas futuras. Los festivos se registran
-- en memoria desde holidays (calendario nacional de Brasil, versión fijada).
WITH dias AS (
 SELECT d::DATE fecha FROM generate_series(CAST(? AS DATE),CAST(? AS DATE),INTERVAL 1 DAY) t(d)
), bf AS (
 SELECT fecha FROM dias
 WHERE month(fecha)=11 AND isodow(fecha)=5 AND day(fecha) BETWEEN 23 AND 29
)
SELECT d.fecha, isodow(d.fecha)::INTEGER dia_semana, day(d.fecha) dia_mes,
 month(d.fecha) mes,
 CASE WHEN f.fecha IS NOT NULL THEN 1 ELSE 0 END festivo,
 CASE WHEN b.fecha IS NOT NULL THEN 1 ELSE 0 END black_friday,
 CASE WHEN EXISTS(SELECT 1 FROM bf WHERE d.fecha BETWEEN bf.fecha+INTERVAL 1 DAY
                   AND bf.fecha+INTERVAL 4 DAY) THEN 1 ELSE 0 END post_black_friday,
 CASE WHEN (month(d.fecha)=12 AND day(d.fecha)>=24)
            OR (month(d.fecha)=1 AND day(d.fecha)=1) THEN 1 ELSE 0 END fin_anio
FROM dias d LEFT JOIN festivos f ON d.fecha=f.fecha LEFT JOIN bf b ON d.fecha=b.fecha
ORDER BY d.fecha;
