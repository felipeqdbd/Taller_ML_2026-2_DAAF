# Auditoría de la solución

Se conciliaron resultados mediante SQL y cálculos independientes. Los ocho modelos se reajustaron en dos orígenes retirando físicamente las compras posteriores. Las siguientes comprobaciones terminaron correctamente.

| Comprobación | Resultado | Evidencia |
|---|---|---|
| Serie conciliada con compras | OK | 567 días consecutivos, 97590 órdenes distintas; exportación idéntica a SQL. |
| Protocolo temporal | OK | 30/12/5 emisiones; los objetivos de las tres etapas no se cruzan; prueba ocupa los últimos 56 días. |
| Predicciones y ajustes de seleccion | OK | 6720 pares; reales, horizontes, convergencia, métricas SQL y referencias conciliados según corresponda. |
| Predicciones y ajustes de calibracion | OK | 336 pares; reales, horizontes, convergencia, métricas SQL y referencias conciliados según corresponda. |
| Predicciones y ajustes de prueba | OK | 1120 pares; reales, horizontes, convergencia, métricas SQL y referencias conciliados según corresponda. |
| Elección reproducible | OK | El modelo final corresponde al mínimo MAE de selección; no se elige por prueba. |
| Ventanas y variables históricas | OK | 477 orígenes y 13356 pares: medias, dispersión, rezagos, día comparable y razones conciliados. |
| Calendario de Black Friday | OK | Coincide con el día posterior al cuarto jueves de noviembre en el calendario disponible. |
| Futuro físicamente retirado | OK | Los ocho modelos reproducen sus 28 pronósticos en el primer origen de selección y el primero de prueba. |
| Intervalos diarios y totales | OK | 16 cuantiles por orden estadístico exacto; límites, sumas y coberturas conciliados sin reutilizar las funciones evaluadas. |
| Pronóstico histórico final | OK | Reajuste reproducible, 28 fechas consecutivas, totales semanales coherentes y reales futuros desconocidos. |
| Notebooks ejecutados y comentados | OK | Tres notebooks con ejecución secuencial, sin errores, comentarios y figuras incrustadas para GitHub. |

## Alcance de la evidencia

La ausencia de discrepancias en estas comprobaciones respalda la consistencia de la ejecución. No garantiza que el modelo funcione en otros períodos. La evaluación es retrospectiva; los errores y los intervalos tienen dependencia temporal. El corte de cobertura sigue siendo una decisión analítica.

Para repetir: `python scripts/auditar.py`, después de `python scripts/ejecutar.py`. Los detalles técnicos están en `resultados/auditoria.json`; las versiones en `resultados/entorno.json`.
