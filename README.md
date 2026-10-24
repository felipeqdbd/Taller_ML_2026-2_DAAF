# Olist: pronóstico de pedidos a 28 días

Solución del **Módulo B (series de tiempo)** del taller de Aprendizaje Automático, sobre la base de datos común del Módulo 0. Responde a la pregunta de planeación: ¿cuántas órdenes recibirá Olist en las próximas semanas? Incluye preparación y calidad de datos, exploración temporal, modelos estadísticos y de ML, evaluación walk-forward, intervalos y auditoría. Los notebooks están ejecutados y comentados en español.

## Ruta de lectura

1. **[Guía completa](documentacion/guia_completa.md):** explica desde cero el problema, cada desarrollo y la interpretación concreta de resultados.
2. [Datos y calidad](notebooks/00_datos.ipynb).
3. [Exploración temporal](notebooks/B_series_01_exploracion.ipynb): incluye una tabla visible de festivos y eventos especiales.
4. [Modelado y pronóstico](notebooks/B_series_02_modelado.ipynb).
5. [Informe PDF](documentacion/informe.pdf), [informe Markdown](documentacion/informe.md) y [auditoría](documentacion/auditoria.md).

## Resultados y lectura correcta

- Serie: **565 días**, 97,091 compras, de 2017-02-01 a 2018-08-19.
- Protocolo: 30 emisiones de selección, 12 de calibración y 5 de prueba. Cada emisión parte de un domingo y cubre 28 días (cuatro semanas lunes–domingo); los orígenes avanzan semanalmente.
- Seleccionado: **SARIMAX_calendario**, MAE 42.20 en selección y 61.50 en prueba. Referencia semanal: 66.42 en prueba. ETS_amortiguado presenta el menor MAE de prueba (60.84), pero no se redefine el ganador usando esa información.
- El objetivo relativo de LightGBM no mejora el promedio en este experimento. La comparación controlada queda documentada con sus resultados.
- **Los intervalos no alcanzan el 90 % nominal:** el principal (conformal relativo) cubre 76.43% diario (107/140) y 80.0% semanal (16/20); el paramétrico de SARIMAX, 73.6%. No se presentan como márgenes operativamente validados al 90 %.
- Pronóstico histórico del lunes 2018-08-20 al domingo 2018-09-16: **7,130.89** como suma de puntos. No equivale automáticamente a media esperada o mediana del total.
- **Evaluación retrospectiva:** las fechas de prueba ya eran conocidas. No es una nueva prueba ciega ni una proyección actual de Olist.

## Reproducir

Entorno utilizado: Python 3.13; versiones exactas fijadas en `requirements.txt` y entorno registrado en `resultados/entorno.json`.

```bash
python -m venv .venv
source .venv/bin/activate
# Windows: .venv\Scripts\activate
python -m pip install -r requirements.txt
python scripts/build_olist_duckdb.py --out data/olist.duckdb
python scripts/ejecutar.py
python scripts/auditar.py
python scripts/generar_documentacion.py
```

Ejecuta desde la raíz del proyecto. La construcción descarga datos públicos y necesita Internet. El script original reemplaza el archivo de salida si existe; no vuelvas a construir una base que quieras conservar. El análisis posterior abre DuckDB con `read_only=True`.

Para explorar interactivamente, usa VS Code con extensión Jupyter y el entorno virtual, o instala JupyterLab. Los resultados incrustados permiten leer los notebooks directamente en GitHub sin ejecutar nada.

Los notebooks son la fuente del análisis: los cambios se hacen directamente en ellos. Después de modificarlos hay que ejecutarlos de nuevo (`scripts/ejecutar.py`), correr la auditoría y regenerar la documentación.

## Estructura

```text
notebooks/       Tres recorridos explicados, código y salidas visibles
sql/             Consultas de calidad, EDA, serie, calendario y variables
src/             Configuración, datos, modelos, métricas e intervalos
scripts/         Construcción, ejecución, auditoría y documentación
resultados/      CSV/JSON derivados, configuración y evidencia
documentacion/  Guía completa, informe PDF/Markdown, auditoría y figuras
data/            Base local reconstruible; excluida de Git
```

## Archivos para consultar resultados

- `metricas_seleccion.csv`, `metricas_prueba.csv`: comparación global de 9 candidatos (MAE, RMSE, MAPE, sMAPE y sesgo).
- `comparacion_componentes.csv`: efecto de variables y objetivo de LightGBM, y de modelar eventos en SARIMAX.
- `errores_por_evento.csv`: error por tipo de día (festivos, Carnaval, Black Friday, fin de año, pre-Navidad, huelga).
- `metricas_horizonte_*`, `metricas_origen_*`, `metricas_semana_*`: detalle temporal.
- `metricas_prueba_igual_peso_fecha.csv`: sensibilidad al peso de fechas solapadas.
- `cuantiles_intervalos*.csv`, `cobertura_*` y `cobertura_metodos.csv`: calibración, amplitud y cobertura de los intervalos conformales y del paramétrico de SARIMAX.
- `pronostico_diario_28_dias.csv` y `pronostico_semanal.csv`: puntos y límites finales; no se suman límites diarios para construir los semanales.
- `auditoria.json`, `entorno.json`, `huellas_csv.json`: evidencia de verificación y reproducción.

## Alcance y atribución

Esta entrega resuelve el Módulo B (series de tiempo) sobre la base común del Módulo 0. El script de construcción suministrado en el curso se conserva. Datos: [Brazilian E-Commerce Public Dataset by Olist](https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce), versión 2 utilizada en esta ejecución. Revisar la licencia **CC BY-NC-SA 4.0** antes de redistribuir datos derivados.

La entrega excluye `data/olist.duckdb`, entornos virtuales y cachés. Está preparada para un repositorio; no se ha publicado en GitHub.
