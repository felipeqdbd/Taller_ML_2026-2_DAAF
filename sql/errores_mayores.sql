-- ============================================================================
-- errores_mayores.sql
-- Propósito:   Pares origen-horizonte con mayor error absoluto de un modelo, con sus eventos.
-- Operaciones:
--   1. Filtra las predicciones del modelo indicado.
--   2. Une las etiquetas de evento de la fecha objetivo (puede haber varias).
--   3. Ordena por error absoluto y conserva los primeros n pares.
-- Parámetros:  1) nombre del modelo; 2) número de pares.
-- Requiere:    vistas en memoria predicciones y etiquetas.
-- Salida:      una fila por par; eventos vacío = sin evento conocido.
-- ============================================================================
SELECT p.origen,p.fecha,p.h,p.real,p.pred,abs(p.real-p.pred) AS error,
       string_agg(e.evento,', ' ORDER BY e.evento) AS eventos
FROM predicciones p LEFT JOIN etiquetas e USING(fecha)
WHERE p.modelo=?
GROUP BY p.origen,p.fecha,p.h,p.real,p.pred
ORDER BY error DESC LIMIT CAST(? AS INTEGER);
