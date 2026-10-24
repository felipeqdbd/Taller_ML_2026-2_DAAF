-- ============================================================================
-- atipicos_stl.sql
-- Propósito:   Días cuyo residuo STL robusto es extremo, con su etiqueta de evento.
-- Operaciones:
--   1. Estandariza el residuo con mediana y MAD (z robusto; 1.4826 hace la MAD
--      comparable con una desviación estándar bajo normalidad).
--   2. Filtra |z| mayor que el umbral y une las etiquetas de eventos del día.
-- Parámetros:  1) umbral de |z| robusto; un valor negativo devuelve todos los días.
-- Requiere:    vistas en memoria residuos (fecha, y, residuo) y etiquetas.
-- Salida:      una fila por día atípico; eventos vacío = sin explicación en el calendario.
-- ============================================================================
WITH centro AS (
 SELECT median(residuo) AS c FROM residuos
), escala AS (
 SELECT c,1.4826*median(abs(r.residuo-c)) AS mad FROM residuos r,centro GROUP BY c
), z AS (
 SELECT r.fecha,r.y,r.residuo,(r.residuo-e.c)/e.mad AS z_robusto FROM residuos r,escala e
)
SELECT z.fecha,isodow(z.fecha)::INTEGER AS dia_semana,z.y,z.residuo,z.z_robusto,
       string_agg(e.evento,', ' ORDER BY e.evento) AS eventos
FROM z LEFT JOIN etiquetas e USING(fecha)
WHERE abs(z.z_robusto)>CAST(? AS DOUBLE)
GROUP BY z.fecha,z.y,z.residuo,z.z_robusto ORDER BY z.fecha;
