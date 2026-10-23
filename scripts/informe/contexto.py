"""Cifras y tablas del informe, calculadas desde resultados/.

Cada número que aparece en el texto sale de aquí: el contenido redactado
(fuente.md) solo usa marcadores {{clave}}. Los formatos siguen la convención
española (coma decimal, punto de miles) con reglas de redondeo fijas:
órdenes y errores en pedidos con 1 decimal, porcentajes con 1 decimal (o
entero en el texto corrido), coeficientes con 2 decimales.
"""
import json
import numpy as np
import pandas as pd
from src.configuracion import ROOT, INICIO, CORTE, FIN, HORIZONTE, SELECCION, CALIBRACION, PRUEBA, EPISODIOS
from src.evaluacion import calibrar

R = ROOT/'resultados'
MESES = 'enero febrero marzo abril mayo junio julio agosto septiembre octubre noviembre diciembre'.split()
# Nombres legibles: los identificadores de código solo aparecen en la tabla de equivalencias.
from src.estilo import NOMBRE  # una sola fuente para figuras, tablas y texto
EVENTO = {'black_friday': 'Black Friday', 'post_black_friday': 'Cuatro días posteriores a Black Friday',
          'fin_anio': 'Fin de año (24-dic a 1-ene)', 'pre_navidad': 'Semana previa a Navidad (14 a 23-dic)',
          'festivo': 'Festivo nacional', 'carnaval': 'Carnaval (lunes y martes)', 'sin_evento': 'Días sin evento',
          'huelga_camioneros': 'Huelga de camioneros', 'mundial_brasil': 'Partidos de Brasil en el Mundial'}


def num(x, d=0):
    """1234.5 -> '1.234,5'."""
    return f'{x:,.{d}f}'.replace(',', '_').replace('.', ',').replace('_', '.')


def pct(x, d=0, signo=False):
    """Proporción -> porcentaje con espacio fino antes de %."""
    s = num(100*x, d)
    if signo and x > 0:
        s = '+' + s
    return s.replace('-', '−') + ' %'


def fecha(f, anio=True):
    f = pd.Timestamp(f)
    return f'{f.day} de {MESES[f.month-1]}' + (f' de {f.year}' if anio else '')


def p_valor(p, limite=None):
    if limite and limite.strip()[:2] in ('<=', '>='):
        return ('≤ ' if limite.strip().startswith('<') else '≥ ') + num(float(limite.split()[-1]), 2)
    return '< 0,001' if p < 0.001 else num(p, 3)


def leer(nombre, **kw):
    return pd.read_csv(R/f'{nombre}.csv', **kw)


def construir():
    """Devuelve (valores, tablas). tablas[clave] = (DataFrame de textos, columnas numéricas, fila resaltada)."""
    v, t = {}, {}
    r = json.loads((R/'resumen.json').read_text(encoding='utf-8'))
    audit = json.loads((R/'auditoria.json').read_text(encoding='utf-8'))
    entorno = json.loads((R/'entorno.json').read_text(encoding='utf-8'))
    G, ML = r['ganador'], r['mejor_ml']
    ms = leer('metricas_seleccion').set_index('modelo'); mt = leer('metricas_prueba').set_index('modelo')
    por_origen_sel = leer('metricas_origen_seleccion'); por_origen_test = leer('metricas_origen_prueba')
    sem_sel = leer('metricas_semana_seleccion'); sem_test = leer('metricas_semana_prueba')
    h_sel = leer('metricas_horizonte_seleccion')
    comp = leer('comparacion_componentes').set_index('comparacion')
    metodos = leer('cobertura_metodos').set_index('metodo_intervalo')
    cs = leer('cobertura_semanal').set_index('metodo_intervalo')
    cal_param = leer('cobertura_metodos_calibracion').iloc[0]
    q = leer('cuantiles_intervalos'); q_ml = leer('cuantiles_intervalos_ml')
    final_s = leer('pronostico_semanal'); final_d = leer('pronostico_diario_28_dias', parse_dates=['fecha'])
    coef = leer('coeficientes_sarimax_final').set_index('parametro')
    ev = leer('errores_por_evento'); mag = leer('magnitud_eventos').set_index('evento')
    est = leer('estacionariedad'); aic = leer('aic_diagnostico'); amp = leer('resumen_amplitud').set_index('ventana')
    perfil = leer('perfil_semanal'); pm = leer('promedio_mensual', parse_dates=['mes']).set_index('mes').media_diaria
    atip = leer('atipicos_stl', parse_dates=['fecha']); imp = leer('importancia_variables')
    por_mes = leer('sesgo_por_mes_prueba', parse_dates=['mes']); aj_sel = leer('ajustes_seleccion')
    tablas_bd = leer('tablas').set_index('tabla').filas; llaves = leer('llaves').set_index('tabla')
    rel = leer('relaciones').iloc[0]; cal0 = leer('calidad').iloc[0]; calx = leer('calidad_extra').iloc[0]
    ident = leer('identidad_cliente').iloc[0]; estados = leer('estados').set_index('order_status').ordenes
    igual = leer('metricas_prueba_igual_peso_fecha')

    # --- Protocolo y datos -------------------------------------------------
    v['fecha_hoy'] = fecha(pd.Timestamp.today())
    v.update(inicio=fecha(INICIO), corte=fecha(CORTE), fin=fecha(FIN), n_dias=num(r['n_dias']),
             total_pedidos=num(r['total_pedidos']), horizonte=str(HORIZONTE),
             n_sel=str(len(SELECCION)), n_cal=str(len(CALIBRACION)), n_prueba=str(len(PRUEBA)),
             primer_origen_sel=fecha(SELECCION[0]), ultimo_origen_sel=fecha(SELECCION[-1]),
             primer_origen_cal=fecha(CALIBRACION[0]), primer_origen_prueba=fecha(PRUEBA[0]),
             prueba_desde=fecha(PRUEBA[0]+pd.Timedelta(days=1)), prueba_hasta=fecha(FIN),
             dias_especif=str((SELECCION[0]-pd.Timestamp(INICIO)).days+1),
             pares_sel=num(len(SELECCION)*HORIZONTE), pares_prueba=num(len(PRUEBA)*HORIZONTE),
             final_desde=fecha(pd.Timestamp(FIN)+pd.Timedelta(days=1)),
             final_hasta=fecha(pd.Timestamp(FIN)+pd.Timedelta(days=HORIZONTE)),
             n_tablas=str(len(tablas_bd)), filas_total=num(tablas_bd.sum()), ordenes=num(cal0.ordenes),
             filas_join=num(rel.filas_join_items_y_pagos), varios_items=num(rel.ordenes_varios_items),
             sin_items=num(cal0.sin_items), sin_pagos=num(cal0.sin_pagos),
             dif_pago=num(cal0.diferencia_pago_mayor_2_centavos), entrega_nula=num(calx.entrega_nula),
             canceladas=num(estados.get('canceled', 0)), indisponibles=num(estados.get('unavailable', 0)),
             entregadas=num(estados.get('delivered', 0)), personas=num(ident.personas_customer_unique_id),
             reviews_rep=num(llaves.loc['order_reviews', 'repetidos']),
             geo_filas=num(llaves.loc['geolocation', 'filas']), geo_prefijos=num(llaves.loc['geolocation', 'distintos']))

    # --- Análisis de la serie ---------------------------------------------
    meseta = pm[pd.Timestamp('2018-01-01'):pd.Timestamp('2018-05-01')]
    pf = perfil.set_index(['ventana', 'dia_semana']).mediana
    a_d = aic[aic.familia.str.startswith('D')].set_index('orden')
    ma_e = aic[aic.familia.str.startswith('E')].MA_estacional
    z_bf = atip.set_index('fecha').z_robusto
    v.update(feb17=num(pm.loc['2017-02-01']), oct17=num(pm.loc['2017-10-01']),
             crecimiento=num(pm.loc['2017-10-01']/pm.loc['2017-02-01'], 1),
             meseta_min=num(meseta.min()), meseta_max=num(meseta.max()),
             lun_pct=pct(pf[('diagnostico', 1)]-1), sab_pct=pct(pf[('diagnostico', 6)]-1),
             lun_pre=num(pf[('preprueba', 1)], 2), lun_diag=num(pf[('diagnostico', 1)], 2),
             sab_pre=num(pf[('preprueba', 6)], 2), sab_diag=num(pf[('diagnostico', 6)], 2),
             dom_diag=num(pf[('diagnostico', 7)], 2), dom_pre=num(pf[('preprueba', 7)], 2),
             r_orig=num(amp.loc['diagnostico', 'corr_original'], 2), r_log=num(amp.loc['diagnostico', 'corr_log'], 2).replace('-', '−'),
             cv=num(amp.loc['diagnostico', 'cv_medio'], 2),
             delta_aic=num(a_d.loc['(1,1,1)', 'delta_AIC'], 1), mejor_orden=a_d.delta_AIC.idxmin(),
             ma_est_min=num(ma_e.min(), 2).replace('-', '−'), ma_est_max=num(ma_e.max(), 2).replace('-', '−'),
             n_atipicos=str(len(atip)), atip_explicados=str(int(atip.eventos.notna().sum())),
             z_junio=num(z_bf.loc[pd.Timestamp('2017-06-21')], 0).replace('-', '−'),
             y_junio=num(atip.set_index('fecha').y.loc[pd.Timestamp('2017-06-21')]),
             z_bf=num(z_bf.loc[pd.Timestamp('2017-11-24')], 0),
             bf_razon=num(mag.loc['black_friday', 'razon_total'], 1), post_razon=num(mag.loc['post_black_friday', 'razon_total'], 1),
             fin_razon=num(mag.loc['fin_anio', 'razon_total'], 2), fest_razon=num(mag.loc['festivo', 'razon_total'], 2),
             fest_min=num(mag.loc['festivo', 'razon_min'], 2), fest_max=num(mag.loc['festivo', 'razon_max'], 2),
             carn_razon=num(mag.loc['carnaval', 'razon_total'], 2), prenav_razon=num(mag.loc['pre_navidad', 'razon_total'], 2),
             prenav_min=num(mag.loc['pre_navidad', 'razon_min'], 2), prenav_max=num(mag.loc['pre_navidad', 'razon_max'], 2),
             huelga_razon=num(mag.loc['huelga_camioneros', 'razon_total'], 2), mundial_razon=num(mag.loc['mundial_brasil', 'razon_total'], 2),
             bf_obs=num(mag.loc['black_friday', 'observado']), bf_esp=num(mag.loc['black_friday', 'esperado']))

    # --- Resultados ---------------------------------------------------------
    hg = h_sel[h_sel.modelo.eq(G)].set_index('h')
    sg = sem_sel[sem_sel.modelo.eq(G)].set_index('semana').MAE
    st = sem_test[sem_test.modelo.eq(G)].set_index('semana').MAE
    se_t = sem_test[sem_test.modelo.eq('Estacional_7')].set_index('semana').MAE
    se_s = sem_sel[sem_sel.modelo.eq('Estacional_7')].set_index('semana').MAE
    mejora_sem_sel = 1 - sg/se_s
    lb = aj_sel[aj_sel.modelo.eq('SARIMAX_calendario')]
    desv = por_origen_sel.groupby('modelo').MAE.std()
    mes_g = por_mes[por_mes.modelo.eq(G)].set_index('mes').sort_index()
    v.update(G=NOMBRE[G], ML=NOMBRE[ML], mejor_prueba=NOMBRE[r['mejor_prueba']],
             mae_sel_g=num(ms.loc[G, 'MAE'], 1), mae_sel_est=num(ms.loc['Estacional_7', 'MAE'], 1),
             mae_sel_ing=num(ms.loc['Ingenuo', 'MAE'], 1), mae_sel_ml=num(ms.loc[ML, 'MAE'], 1),
             mae_sel_sin=num(ms.loc['SARIMAX_solo_semana', 'MAE'], 1), mae_sel_ets=num(ms.loc['ETS_amortiguado', 'MAE'], 1),
             rmse_sel_g=num(ms.loc[G, 'RMSE'], 1), mape_sel_g=num(ms.loc[G, 'MAPE'], 1),
             mejora_sel=pct(1-ms.loc[G, 'MAE']/ms.loc['Estacional_7', 'MAE']),
             mejora_sel_ing=pct(1-ms.loc[G, 'MAE']/ms.loc['Ingenuo', 'MAE']),
             desv_g=num(desv[G], 0), desv_est=num(desv['Estacional_7'], 0),
             mae_h1=num(hg.loc[1, 'MAE'], 0), mae_h_final=num(hg.loc[22:28, 'MAE'].mean(), 0),
             mape_h1=num(hg.loc[1, 'MAPE'], 0), mape_h_final=num(hg.loc[22:28, 'MAPE'].mean(), 0),
             sem_sel=' → '.join(num(sg.loc[k], 0) for k in range(1, 5)),
             mejora_sem_min=pct(mejora_sem_sel.min()), mejora_sem_max=pct(mejora_sem_sel.max()),
             d_eventos=num(-comp.loc['Eventos de calendario en SARIMAX', 'diferencia_MAE'], 1),
             o_eventos=str(int(comp.loc['Eventos de calendario en SARIMAX', 'origenes_mejora'])),
             d_ampl_abs=num(comp.loc['Variables con objetivo absoluto', 'diferencia_MAE'], 1),
             d_ampl_rel=num(comp.loc['Variables con objetivo relativo', 'diferencia_MAE'], 1),
             d_rel_base=num(comp.loc['Objetivo con variables básicas', 'diferencia_MAE'], 1),
             d_rel_ampl=num(comp.loc['Objetivo con variables ampliadas', 'diferencia_MAE'], 1),
             lb_rech=str(int(lb.Ljung_Box_p7.lt(.05).sum())), lb_n=str(len(lb)),
             mae_test_g=num(mt.loc[G, 'MAE'], 1), mae_test_est=num(mt.loc['Estacional_7', 'MAE'], 1),
             mae_test_ing=num(mt.loc['Ingenuo', 'MAE'], 1), mae_test_mejor=num(mt.loc[r['mejor_prueba'], 'MAE'], 1),
             mae_test_ml=num(mt.loc[ML, 'MAE'], 1), sesgo_test_g=num(mt.loc[G, 'sesgo'], 0).replace('-', '−'),
             mejora_test=pct(1-mt.loc[G, 'MAE']/mt.loc['Estacional_7', 'MAE']),
             mae_test_sem1=num(st.loc[1], 0), mae_test_est_sem1=num(se_t.loc[1], 0),
             mae_test_sem34=num((st.loc[3]+st.loc[4])/2, 0),
             desv_test=num(por_origen_test.groupby('modelo').MAE.std()[G], 0),
             real_jul=num(mes_g.real_medio.iloc[1]), real_ago=num(mes_g.real_medio.iloc[2]),
             salto_ago=pct(mes_g.real_medio.iloc[2]/mes_g.real_medio.iloc[1]-1),
             sesgo_jul=pct(mes_g.sesgo_pct.iloc[1]/100), sesgo_ago=pct(mes_g.sesgo_pct.iloc[2]/100))

    # --- Incertidumbre -------------------------------------------------------
    qd = q[q.unidad.eq('diaria') & q.metodo.eq('relativo')].set_index('semana').cuantil
    cal_pred = leer('predicciones_calibracion', parse_dates=['fecha'])
    huelga = EPISODIOS[EPISODIOS.evento.eq('huelga_camioneros')].iloc[0]
    sin_huelga = calibrar(cal_pred[~cal_pred.fecha.between(huelga.desde, huelga.hasta)], metodo='relativo').set_index('semana').cuantil
    v.update(cob_dia=pct(metodos.loc['relativo', 'cobertura'], 1), cub_dia=str(int(metodos.loc['relativo', 'cubiertos'])),
             n_dia=str(int(metodos.loc['relativo', 'n'])), cob_sem=pct(cs.loc['relativo', 'cobertura']),
             cub_sem=str(int(cs.loc['relativo', 'cubiertos'])), n_sem=str(int(cs.loc['relativo', 'n'])),
             cob_abs=pct(metodos.loc['absoluto', 'cobertura'], 1), cob_param=pct(metodos.loc['parametrico_sarimax', 'cobertura'], 1),
             cob_ml=pct(metodos.loc['conformal_ml', 'cobertura'], 1), cob_param_cal=pct(cal_param.cobertura, 1),
             ancho_rel=num(metodos.loc['relativo', 'ancho_medio']), ancho_abs=num(metodos.loc['absoluto', 'ancho_medio']),
             q1=num(qd.loc[1], 2), q_resto_min=num(qd.loc[2:4].min(), 2), q_resto_max=num(qd.loc[2:4].max(), 2),
             q1_sin_huelga=num(sin_huelga.loc[1], 2), q2=num(qd.loc[2], 2), q2_sin_huelga=num(sin_huelga.loc[2], 2),
             q1_pct=pct(qd.loc[1]), rango_77='77', n_err='84')

    # --- Interpretación y pronóstico final -----------------------------------
    ef = lambda p: np.expm1(coef.loc[p, 'coeficiente'])
    dias = final_d.assign(d=final_d.fecha.dt.dayofweek).groupby('d').pred.mean()
    evp = ev[ev.etapa.eq('seleccion')].pivot(index='evento', columns='modelo', values='MAE')
    ev_cal = ev[ev.etapa.eq('calibracion') & ev.modelo.eq(G)].set_index('evento')
    tend = imp.set_index('variable').proporcion
    v.update(ef_lun=pct(ef('dia_1')), ef_sab=pct(-ef('dia_6')), ef_bf=num(1+ef('black_friday'), 1),
             ef_post=pct(ef('post_black_friday')), ef_fin=pct(-ef('fin_anio')), ef_fest=pct(-ef('festivo')),
             ef_carn=pct(-ef('carnaval')), ar=num(coef.loc['ar.L1', 'coeficiente'], 2),
             ma=num(coef.loc['ma.L1', 'coeficiente'], 2).replace('-', '−'),
             err_fest_sin=num(evp.loc['festivo', 'SARIMAX_solo_semana'], 0), err_fest_con=num(evp.loc['festivo', G], 0),
             err_fin_sin=num(evp.loc['fin_anio', 'SARIMAX_solo_semana'], 0), err_fin_con=num(evp.loc['fin_anio', G], 0),
             err_carn_sin=num(evp.loc['carnaval', 'SARIMAX_solo_semana'], 0), err_carn_con=num(evp.loc['carnaval', G], 0),
             err_prenav_sin=num(evp.loc['pre_navidad', 'SARIMAX_solo_semana'], 0), err_prenav_con=num(evp.loc['pre_navidad', G], 0),
             err_normal=num(evp.loc['sin_evento', G], 0), err_bf=num(evp.loc['black_friday', G], 0),
             err_huelga=num(ev_cal.loc['huelga_camioneros', 'MAE'], 0), err_cal_normal=num(ev_cal.loc['sin_evento', 'MAE'], 0),
             sesgo_huelga=num(ev_cal.loc['huelga_camioneros', 'sesgo'], 0),
             tendencia_pct=pct(tend.get('tendencia', 0)), dia_semana_pct=pct(tend.get('dia_semana', 0)),
             total_final=num(r['total_puntos_28_dias']), semana_media=num(final_s.pred.mean()),
             lunes_final=num(dias.loc[0]), sabado_final=num(dias.loc[5]),
             festivo_final=num(final_d.set_index('fecha').pred.loc[pd.Timestamp('2018-09-07')]),
             viernes_final=num(final_d.set_index('fecha').pred.loc[pd.Timestamp('2018-08-24')]),
             sem1_final=num(final_s.pred.iloc[0]), sem1_inf=num(final_s.inferior.iloc[0]), sem1_sup=num(final_s.superior.iloc[0]),
             n_auditoria=str(len(audit['comprobaciones'])), python=entorno['python'])

    # --- Tablas -------------------------------------------------------------
    def tabla(clave, df, numericas=(), resaltar=None):
        t[clave] = (df.astype(str), list(numericas), resaltar)

    tabla('respuesta', pd.DataFrame({
        'Semana': final_s.semana.astype(int),
        'Lunes a domingo': [f'{pd.Timestamp(a).day}-{MESES[pd.Timestamp(a).month-1][:3]} a {pd.Timestamp(b).day}-{MESES[pd.Timestamp(b).month-1][:3]}' for a, b in zip(final_s.desde, final_s.hasta)],
        'Pronóstico (órdenes)': final_s.pred.map(num),
        'Intervalo del 90 % nominal': [f'{num(a)} – {num(b)}' for a, b in zip(final_s.inferior, final_s.superior)]}),
        ['Pronóstico (órdenes)', 'Intervalo del 90 % nominal'])
    tabla('calidad', pd.DataFrame([
        ['Unicidad de order_id', f'{num(cal0.ordenes)} órdenes, {int(cal0.ids_duplicados)} duplicadas', 'orders es la unidad de conteo'],
        ['Unión con ítems y pagos (1:N)', f'{num(rel.filas_join_items_y_pagos)} filas', 'Se cuenta antes de cualquier unión'],
        ['Fechas de compra', f'{int(cal0.compras_sin_fecha)} faltantes; {int(cal0.entrega_antes_compra)} entregas previas a la compra', 'La fecha de compra es confiable'],
        ['Órdenes sin ítems / sin pagos', f'{num(cal0.sin_items)} / {num(cal0.sin_pagos)}', 'Se conservan: la compra ocurrió'],
        ['Ítems frente a pagos (> 2 centavos)', f'{num(cal0.diferencia_pago_mayor_2_centavos)} órdenes', 'Se informa; no afecta la fecha'],
        ['Aprobación / entrega sin fecha', f'{num(calx.aprobacion_nula)} / {num(calx.entrega_nula)}', 'Esperable en canceladas o en curso'],
        ['review_id repetido', f'{num(llaves.loc["order_reviews","repetidos"])} casos', 'Las reseñas no intervienen'],
        ['Identidad del comprador', f'{num(ident.personas_customer_unique_id)} personas para {num(ident.registros_customers)} customer_id', 'La persona es customer_unique_id'],
    ], columns=['Comprobación', 'Resultado', 'Decisión']))
    etapas = pd.DataFrame([
        ['Validación (selección)', len(SELECCION), f'{fecha(SELECCION[0])} a {fecha(SELECCION[-1])}', 'Elegir el modelo por MAE'],
        ['Calibración', len(CALIBRACION), f'{fecha(CALIBRACION[0])} a {fecha(CALIBRACION[-1])}', 'Estimar los intervalos'],
        ['Prueba', len(PRUEBA), f'{fecha(PRUEBA[0])} a {fecha(PRUEBA[-1])}', 'Medir el desempeño final una vez']],
        columns=['Etapa', 'Emisiones', 'Orígenes (domingos)', 'Función'])
    tabla('etapas', etapas, ['Emisiones'])
    serie_est = {'nivel': 'Nivel', 'diferencia_1': 'Primera diferencia (Δ)', 'diferencia_7': 'Diferencia semanal (Δ₇)', 'diferencia_1_7': 'Ambas (Δ y Δ₇)'}
    tabla('adf', pd.DataFrame({
        'Serie en log(1 + y)': est.serie.map(serie_est), 'n': est.n.astype(int),
        'p ADF': [p_valor(p) for p in est.ADF_p], 'p KPSS': [p_valor(p, l) for p, l in zip(est.KPSS_p_tabla, est.KPSS_limite)],
        'Conclusión conjunta': est.conclusion.str.capitalize()}), ['n', 'p ADF', 'p KPSS'])
    tabla('eventos', pd.DataFrame([
        ['Black Friday', f'× {num(mag.loc["black_friday","razon_total"],1)}', 'Sí', 'Modelar'],
        ['Cuatro días posteriores a Black Friday', f'× {num(mag.loc["post_black_friday","razon_total"],1)}', 'Sí', 'Modelar'],
        ['Fin de año (24-dic a 1-ene)', f'× {num(mag.loc["fin_anio","razon_total"],2)}', 'Sí', 'Modelar'],
        ['Festivos nacionales', f'× {num(mag.loc["festivo","razon_total"],2)}', 'Sí', 'Modelar'],
        ['Carnaval (2018)', f'× {num(mag.loc["carnaval","razon_total"],2)}', 'Sí', 'Modelar'],
        ['Semana previa a Navidad', f'× {num(mag.loc["pre_navidad","razon_total"],2)}', 'Sí', 'Marcar (solo observada en validación)'],
        ['Huelga de camioneros (11 días)', f'× {num(mag.loc["huelga_camioneros","razon_total"],2)}', 'No', 'Marcar (sin indicador futuro)'],
        ['Arranque 2016 y truncamiento final', '—', '—', 'Excluir (artefacto de datos)']],
        columns=['Episodio', 'Observado / esperado', '¿Fecha conocida de antemano?', 'Tratamiento']), ['Observado / esperado'])
    tabla('variables', pd.DataFrame([
        ['Historia al cierre del origen', 'Valor del origen y rezagos de 1 a 6, 13 y 27 días; medias de 7, 28 y 91 días; desviación de 28 días'],
        ['Día comparable', 'Último valor y media de las 4 semanas previas del mismo día de la semana que la fecha objetivo'],
        ['Versiones relativas', 'Rezagos y día comparable expresados en log respecto a la media de 28 días'],
        ['Calendario de la fecha objetivo', 'Horizonte h, día de la semana y del mes, mes, índice de tiempo y los cinco indicadores de eventos']],
        columns=['Grupo', 'Variables (calculadas en SQL con ventanas que terminan en el origen)']))
    tabla('candidatos', pd.DataFrame([
        [NOMBRE['Ingenuo'], 'Repite el último valor observado', 'Regla (línea base)'],
        [NOMBRE['Estacional_7'], 'Repite el valor del mismo día de la semana anterior', 'Regla (línea base)'],
        [NOMBRE['ETS_amortiguado'], 'Nivel, tendencia amortiguada y semana aditiva sobre log(1 + y)', 'Recursiva'],
        [NOMBRE['SARIMAX_solo_semana'], 'Errores ARIMA(1,1,1) en log(1 + y) y seis indicadores de día', 'Recursiva'],
        [NOMBRE['SARIMAX_calendario'], 'Lo anterior más cinco indicadores de eventos de calendario', 'Recursiva'],
        ['LightGBM (cuatro variantes)', 'Variables básicas o ampliadas × objetivo absoluto o relativo; 300 árboles de 7 hojas, pérdida L1', 'Directa global']],
        columns=['Modelo', 'Estructura', 'Estrategia multipaso']))

    def metricas(m, base):
        orden = m.sort_values('MAE')
        df = pd.DataFrame({'Modelo': orden.index.map(NOMBRE), 'MAE': orden.MAE.map(lambda x: num(x, 1)),
                           'RMSE': orden.RMSE.map(lambda x: num(x, 1)), 'MAPE (%)': orden.MAPE.map(lambda x: num(x, 1)),
                           'sMAPE (%)': orden.sMAPE.map(lambda x: num(x, 1)), 'Sesgo': orden.sesgo.map(lambda x: num(x, 1).replace('-', '−')),
                           'Mejora (%)': (100*(1-orden.MAE/m.loc[base, 'MAE'])).map(lambda x: num(x, 1).replace('-', '−'))})
        return df, list(orden.index).index(G)
    df, i = metricas(ms, 'Estacional_7'); tabla('validacion', df, ['MAE', 'RMSE', 'MAPE (%)', 'sMAPE (%)', 'Sesgo', 'Mejora (%)'], i)
    df, i = metricas(mt, 'Estacional_7'); tabla('prueba', df, ['MAE', 'RMSE', 'MAPE (%)', 'sMAPE (%)', 'Sesgo', 'Mejora (%)'], i)
    tabla('semanas', pd.DataFrame({'Semana del horizonte': ['1 (h = 1–7)', '2 (h = 8–14)', '3 (h = 15–21)', '4 (h = 22–28)'],
        f'{NOMBRE[G]} · validación': [num(sg.loc[k], 1) for k in range(1, 5)],
        'Estacional · validación': [num(se_s.loc[k], 1) for k in range(1, 5)],
        f'{NOMBRE[G]} · prueba': [num(st.loc[k], 1) for k in range(1, 5)],
        'Estacional · prueba': [num(se_t.loc[k], 1) for k in range(1, 5)]}),
        [f'{NOMBRE[G]} · validación', 'Estacional · validación', f'{NOMBRE[G]} · prueba', 'Estacional · prueba'])
    nombres_comp = {'Variables con objetivo absoluto': 'LightGBM: ampliar variables (objetivo absoluto)',
                    'Variables con objetivo relativo': 'LightGBM: ampliar variables (objetivo relativo)',
                    'Objetivo con variables básicas': 'LightGBM: objetivo relativo (variables básicas)',
                    'Objetivo con variables ampliadas': 'LightGBM: objetivo relativo (variables ampliadas)',
                    'Eventos de calendario en SARIMAX': 'SARIMAX: añadir indicadores de eventos'}
    c2 = comp.reset_index()
    tabla('componentes', pd.DataFrame({'Cambio evaluado': c2.comparacion.map(nombres_comp),
        'Δ MAE (órdenes)': c2.diferencia_MAE.map(lambda x: ('+' if x > 0 else '') + num(x, 1).replace('-', '−')),
        'Orígenes en que mejora': [f'{a} de {b}' for a, b in zip(c2.origenes_mejora, c2.origenes)]}),
        ['Δ MAE (órdenes)', 'Orígenes en que mejora'])
    nombres_int = {'relativo': f'Conformal relativo · {NOMBRE[G]} (principal)', 'absoluto': f'Conformal absoluto · {NOMBRE[G]}',
                   'parametrico_sarimax': 'Paramétrico · SARIMAX con calendario', 'conformal_ml': f'Conformal relativo · {NOMBRE[ML]}'}
    mi = metodos.reindex(['relativo', 'parametrico_sarimax', 'absoluto', 'conformal_ml'])
    tabla('intervalos', pd.DataFrame({'Intervalo del 90 % nominal': mi.index.map(nombres_int),
        'Cobertura': mi.cobertura.map(lambda x: pct(x, 1)), 'Pares cubiertos': [f'{int(a)} de {int(b)}' for a, b in zip(mi.cubiertos, mi.n)],
        'Amplitud media (órdenes)': mi.ancho_medio.map(lambda x: num(x, 0))}),
        ['Cobertura', 'Pares cubiertos', 'Amplitud media (órdenes)'], 0)
    terminos = [('dia_1', 'Lunes'), ('dia_2', 'Martes'), ('dia_3', 'Miércoles'), ('dia_4', 'Jueves'), ('dia_5', 'Viernes'),
                ('dia_6', 'Sábado'), ('festivo', 'Festivo nacional'), ('carnaval', 'Carnaval'), ('black_friday', 'Black Friday'),
                ('post_black_friday', 'Cuatro días posteriores a Black Friday'), ('fin_anio', 'Fin de año'),
                ('ar.L1', 'AR(1) de los errores'), ('ma.L1', 'MA(1) de los errores')]
    tabla('coeficientes', pd.DataFrame({'Término': [n for _, n in terminos],
        'Coeficiente (log)': [num(coef.loc[k, 'coeficiente'], 2).replace('-', '−') for k, _ in terminos],
        'Efecto aproximado': [pct(np.expm1(coef.loc[k, 'coeficiente']), 0, signo=True) if not k.startswith(('ar', 'ma')) else '—' for k, _ in terminos]}),
        ['Coeficiente (log)', 'Efecto aproximado'])
    orden_ev = ['black_friday', 'post_black_friday', 'fin_anio', 'pre_navidad', 'festivo', 'carnaval', 'sin_evento']
    fechas_ev = ev[ev.etapa.eq('seleccion')].groupby('evento').fechas.max()
    tabla('errores_evento', pd.DataFrame({'Tipo de día': [EVENTO[e] for e in orden_ev], 'Fechas': [str(int(fechas_ev[e])) for e in orden_ev],
        'Estacional': [num(evp.loc[e, 'Estacional_7'], 0) for e in orden_ev],
        'SARIMAX sin eventos': [num(evp.loc[e, 'SARIMAX_solo_semana'], 0) for e in orden_ev],
        'SARIMAX con calendario': [num(evp.loc[e, G], 0) for e in orden_ev],
        'LightGBM básico': [num(evp.loc[e, ML], 0) for e in orden_ev]}),
        ['Fechas', 'Estacional', 'SARIMAX sin eventos', 'SARIMAX con calendario', 'LightGBM básico'])
    # Anexos.
    tabla('glosario', pd.DataFrame({'Nombre en el texto': list(NOMBRE.values()), 'Identificador en el código': list(NOMBRE.keys())}))
    tabla('versiones', pd.DataFrame([['Python', entorno['python']], *entorno['paquetes'].items()], columns=['Paquete', 'Versión']))
    # Los nombres de etapa llegan sin tilde desde los identificadores internos de auditar.py.
    comprob = pd.DataFrame(audit['comprobaciones'])[['comprobacion', 'estado']]
    comprob['comprobacion'] = comprob.comprobacion.str.replace('seleccion', 'selección').str.replace('calibracion', 'calibración')
    tabla('auditoria', comprob.rename(columns={'comprobacion': 'Comprobación independiente', 'estado': 'Estado'}))
    ig = igual.set_index('modelo').sort_values('MAE')
    tabla('igual_peso', pd.DataFrame({'Modelo': ig.index.map(NOMBRE), 'MAE': ig.MAE.map(lambda x: num(x, 1)), 'RMSE': ig.RMSE.map(lambda x: num(x, 1)),
        'MAPE (%)': ig.MAPE.map(lambda x: num(x, 1)), 'sMAPE (%)': ig.sMAPE.map(lambda x: num(x, 1))}), ['MAE', 'RMSE', 'MAPE (%)', 'sMAPE (%)'])
    qq = q[q.unidad.eq('diaria')].pivot(index='semana', columns='metodo', values='cuantil')
    tabla('cuantiles', pd.DataFrame({'Semana del horizonte': qq.index.astype(int), 'Relativo (fracción de 1 + ŷ)': qq.relativo.map(lambda x: num(x, 2)),
        'Relativo sin huelga': sin_huelga.reindex(qq.index).map(lambda x: num(x, 2)), 'Absoluto (órdenes)': qq.absoluto.map(lambda x: num(x, 0)),
        f'Relativo · {NOMBRE[ML]}': q_ml.set_index('semana').cuantil.reindex(qq.index).map(lambda x: num(x, 2))}),
        ['Relativo (fracción de 1 + ŷ)', 'Relativo sin huelga', 'Absoluto (órdenes)', f'Relativo · {NOMBRE[ML]}'])
    return v, t
