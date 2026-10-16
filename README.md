# Olist: pronóstico de pedidos a 28 días

Solución autónoma de los **Módulos 0 y B** del taller de Aprendizaje Automático. Incluye preparación y calidad de datos, exploración temporal, modelos estadísticos y de ML, evaluación semanal, intervalos y auditoría. Los notebooks están ejecutados y comentados en español.

## Ruta de lectura

1. **[Guía completa](documentacion/guia_completa.md):** explica desde cero el problema, cada desarrollo y la interpretación concreta de resultados.
2. [Datos y calidad](notebooks/00_datos_y_calidad.ipynb).
3. [Exploración temporal](notebooks/01_exploracion_temporal.ipynb): incluye una tabla visible de festivos y eventos especiales.
4. [Modelado y pronóstico](notebooks/02_modelado_y_pronostico.ipynb).
5. [Informe PDF](documentacion/informe.pdf), [informe Markdown](documentacion/informe.md) y [auditoría](documentacion/auditoria.md).

## Resultados y lectura correcta

- Serie: **567 días**, 97,590 compras, de 2017-02-01 a 2018-08-21.
- Protocolo: 30 emisiones de selección, 12 de calibración y 5 de prueba. Cada emisión cubre 28 días; los orígenes avanzan semanalmente.
- Seleccionado: **SARIMAX_calendario**, MAE 43.11 en selección y 65.82 en prueba. Referencia semanal: 67.02 en prueba. ETS_amortiguado tiene el menor MAE observado en prueba; se mantiene la elección previa.
- El objetivo relativo de LightGBM no mejora el promedio en este experimento. La comparación controlada queda documentada con sus resultados.
- **Los intervalos relativos no alcanzan el 90 % nominal:** cobertura diaria 76.43% (107/140) y semanal 80.0% (16/20). No se presentan como márgenes operativamente validados al 90 %.
- Pronóstico histórico del 22 de agosto al 18 de septiembre de 2018: **6,460.58** como suma de puntos. No equivale automáticamente a media esperada o mediana del total.
- **Evaluación retrospectiva:** las fechas de prueba ya eran conocidas. No es una nueva prueba ciega ni una proyección actual de Olist.

## Reproducir

Entorno utilizado: Python 3.12; versiones directas fijadas en `requirements.txt` y entorno registrado en `resultados/entorno.json`.

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

`crear_notebooks.py` contiene su fuente editorial; regenerarlos elimina sus salidas. Solo se necesita al mantener el material: después hay que ejecutar nuevamente los notebooks y la auditoría.

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

- `metricas_seleccion.csv`, `metricas_prueba.csv`: comparación global de ocho candidatos.
- `comparacion_componentes.csv`: efecto de variables y objetivo de LightGBM.
- `metricas_horizonte_*`, `metricas_origen_*`, `metricas_semana_*`: detalle temporal.
- `metricas_prueba_igual_peso_fecha.csv`: sensibilidad al peso de fechas solapadas.
- `cuantiles_intervalos.csv` y `cobertura_*`: calibración, amplitud y cobertura verificables.
- `pronostico_diario_28_dias.csv` y `pronostico_semanal.csv`: puntos y límites finales; no se suman límites diarios para construir los semanales.
- `auditoria.json`, `entorno.json`, `huellas_csv.json`: evidencia de verificación y reproducción.

## Alcance y atribución

No incluye módulos A, C o D ni la extensión opcional por categoría/estado. El script de construcción suministrado en el curso se conserva. Datos: [Brazilian E-Commerce Public Dataset by Olist](https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce), versión 2 utilizada en esta ejecución. Revisar la licencia **CC BY-NC-SA 4.0** antes de redistribuir datos derivados.

La entrega excluye `data/olist.duckdb`, entornos virtuales y cachés. Está preparada para un repositorio; no se ha publicado en GitHub.
