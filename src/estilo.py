"""Estilo común de figuras y tablas de los notebooks.

Las figuras usan Source Sans 3 (recursos/fuentes/, licencia OFL), la misma familia
de los títulos del informe; si no está, matplotlib recurre a DejaVu Sans. Cada
modelo tiene un color y además un trazo propio (línea y marcador) para que las
series se distingan también en impresión en escala de grises.
"""
from IPython.display import display
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
from matplotlib import font_manager
from .configuracion import ROOT

TINTA, TENUE = '#2b2b2b', '#8a8984'
# Etapas del protocolo y ventanas de análisis.
ETAPA = {'diagnostico': '#7b5ea7', 'seleccion': '#2a78d6', 'calibracion': '#1baf7a', 'prueba': '#eb6834'}
FONDO = {'diagnostico': '#ece6f5', 'seleccion': '#dceafb', 'calibracion': '#d9f1e6', 'prueba': '#fbe3d7'}
# Un color fijo por modelo en todas las figuras.
MODELO = {'Ingenuo': '#e87ba4', 'Estacional_7': '#eda100', 'ETS_amortiguado': '#1baf7a',
          'SARIMAX_solo_semana': '#8fb8ec', 'SARIMAX_calendario': '#2a78d6',
          'LGBM_base_absoluto': '#f2a07b', 'LGBM_amplio_absoluto': '#c4501f',
          'LGBM_base_relativo': '#eb6834', 'LGBM_amplio_relativo': '#9c3d12'}
# Nombre legible de cada candidato para leyendas, tablas e informe (el identificador queda en el código).
NOMBRE = {'Ingenuo': 'Ingenuo', 'Estacional_7': 'Estacional semanal', 'ETS_amortiguado': 'ETS amortiguado',
          'SARIMAX_solo_semana': 'SARIMAX sin eventos', 'SARIMAX_calendario': 'SARIMAX con calendario',
          'LGBM_base_absoluto': 'LightGBM básico, objetivo absoluto', 'LGBM_amplio_absoluto': 'LightGBM ampliado, objetivo absoluto',
          'LGBM_base_relativo': 'LightGBM básico, objetivo relativo', 'LGBM_amplio_relativo': 'LightGBM ampliado, objetivo relativo'}
# (estilo de línea, marcador): redundancia visual independiente del color.
TRAZO = {'Ingenuo': (':', 'x'), 'Estacional_7': ('--', 's'), 'ETS_amortiguado': ('-.', '^'),
         'SARIMAX_solo_semana': ((0, (5, 2, 1, 2)), 'v'), 'SARIMAX_calendario': ('-', 'o'),
         'LGBM_base_absoluto': ((0, (6, 2)), 'D'), 'LGBM_amplio_absoluto': ((0, (2, 1)), 'P'),
         'LGBM_base_relativo': ((0, (4, 1, 1, 1)), 'X'), 'LGBM_amplio_relativo': ((0, (1, 1)), '*')}
MESES = 'ene feb mar abr may jun jul ago sep oct nov dic'.split()
DIAS = ['lun', 'mar', 'mié', 'jue', 'vie', 'sáb', 'dom']


def aplicar_estilo():
    """Registra Source Sans 3 si está disponible y fija los parámetros de matplotlib."""
    for archivo in (ROOT/'recursos'/'fuentes').glob('SourceSans3-*.ttf'):
        font_manager.fontManager.addfont(str(archivo))
    plt.rcParams.update({
        'font.family': ['Source Sans 3', 'DejaVu Sans'], 'font.size': 10.5,
        'figure.figsize': (12, 4), 'figure.dpi': 100, 'savefig.dpi': 160, 'savefig.bbox': 'tight',
        'figure.facecolor': '#fcfcfb', 'axes.facecolor': '#fcfcfb', 'savefig.facecolor': '#fcfcfb',
        'axes.spines.top': False, 'axes.spines.right': False, 'axes.edgecolor': TENUE,
        'axes.labelcolor': '#52514e', 'xtick.color': '#52514e', 'ytick.color': '#52514e',
        'axes.grid': True, 'grid.color': '#e6e5e0', 'grid.linewidth': .8,
        # 'bold' existe en Source Sans 3 y en DejaVu: evita avisos de la fuente de respaldo.
        'axes.titlesize': 12.5, 'axes.titleweight': 'bold', 'axes.titlelocation': 'left',
        'axes.labelsize': 10.5, 'legend.fontsize': 9.5, 'lines.linewidth': 1.6, 'legend.frameon': False})


def trazo(modelo, **extra):
    """Argumentos de plot para un modelo: color, línea y marcador."""
    linea, marcador = TRAZO.get(modelo, ('-', None))
    return dict(color=MODELO.get(modelo, TINTA), linestyle=linea, marker=marcador, **extra)


def fechas_es(ax, paso='mes', intervalo=1):
    """Marcas del eje x en español: cada mes ('feb-17') o cada lunes ('6 nov')."""
    if paso == 'mes':
        ax.xaxis.set_major_locator(mdates.MonthLocator(interval=intervalo))
        texto = lambda d: f'{MESES[d.month-1]}-{d:%y}'
    else:
        ax.xaxis.set_major_locator(mdates.WeekdayLocator(byweekday=mdates.MO, interval=intervalo))
        texto = lambda d: f'{d.day} {MESES[d.month-1]}'
    ax.xaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: texto(mdates.num2date(x))))


def figura(nombre):
    """Ajusta márgenes, guarda la figura en documentacion/figuras/ y la muestra."""
    plt.tight_layout()
    plt.savefig(ROOT/'documentacion'/'figuras'/f'{nombre}.png')
    plt.show()


def mostrar(tabla, titulo, nota=None):
    """Imprime un título en lenguaje natural antes de la tabla: así cada salida se entiende sin leer el código."""
    print(f'\n■ {titulo}')
    if nota:
        print(f'  {nota}')
    display(tabla)
