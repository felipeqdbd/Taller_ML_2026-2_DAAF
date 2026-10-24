-- ============================================================================
-- calendario.sql
-- Propósito:   Atributos de calendario conocidos de antemano (incluye días futuros del horizonte).
-- Operaciones:
--   1. Genera todas las fechas entre los límites.
--   2. Identifica Black Friday: viernes de noviembre entre el 23 y el 29.
--   3. Une con las vistas en memoria festivos y carnavales y marca festivo,
--      carnaval, Black Friday, cuatro días posteriores y fin de año con indicadores 0/1.
-- Parámetros:  1) fecha inicial; 2) fecha final (fin de la serie + horizonte).
-- Requiere:    vistas en memoria festivos y carnavales, registradas desde Python (con.register).
-- Salida:      una fila por día con sus indicadores.
-- ============================================================================
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
 CASE WHEN EXISTS(SELECT 1 FROM carnavales k WHERE k.fecha=d.fecha) THEN 1 ELSE 0 END carnaval,
 CASE WHEN b.fecha IS NOT NULL THEN 1 ELSE 0 END black_friday,
 CASE WHEN EXISTS(SELECT 1 FROM bf WHERE d.fecha BETWEEN bf.fecha+INTERVAL 1 DAY
                   AND bf.fecha+INTERVAL 4 DAY) THEN 1 ELSE 0 END post_black_friday,
 CASE WHEN (month(d.fecha)=12 AND day(d.fecha)>=24)
            OR (month(d.fecha)=1 AND day(d.fecha)=1) THEN 1 ELSE 0 END fin_anio
FROM dias d LEFT JOIN festivos f ON d.fecha=f.fecha LEFT JOIN bf b ON d.fecha=b.fecha
ORDER BY d.fecha;
