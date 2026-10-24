"""Sistema visual del informe: fuentes, paleta, estilos de párrafo y de tabla, páginas.

Texto en Source Serif 4 y títulos, tablas y pies en Source Sans 3 (recursos/fuentes/,
licencia OFL). Si faltan, se usan DejaVu Serif y DejaVu Sans de matplotlib, que
cubren los mismos signos (tildes, eñes, ≈, −, ×, ≤).
"""
from pathlib import Path
import matplotlib
from reportlab.lib import colors
from reportlab.lib.enums import TA_JUSTIFY, TA_LEFT, TA_CENTER, TA_RIGHT
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import cm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from src.configuracion import ROOT

PAGINA = (21*cm, 29.7*cm)
MARGEN = dict(left=2.2*cm, right=2.2*cm, top=2.3*cm, bottom=2.2*cm)
ANCHO = PAGINA[0]-MARGEN['left']-MARGEN['right']

TINTA = colors.HexColor('#1F3A5F')      # títulos y filetes principales
ACENTO = colors.HexColor('#2A78D6')     # mismo azul de las figuras
TEXTO = colors.HexColor('#24272B')
GRIS = colors.HexColor('#52514E')
GRIS_CLARO = colors.HexColor('#8A8984')
FILETE = colors.HexColor('#C9CDD3')
FONDO_SUAVE = colors.HexColor('#F5F7FA')


def registrar_fuentes():
    """Registra las familias 'Texto' y 'Titulos'; devuelve si se usan las fuentes del proyecto."""
    fuentes = ROOT/'recursos'/'fuentes'
    propias = {'Texto': ('SourceSerif4-Regular', 'SourceSerif4-Bold', 'SourceSerif4-It', 'SourceSerif4-Semibold'),
               'Titulos': ('SourceSans3-Regular', 'SourceSans3-Bold', 'SourceSans3-It', 'SourceSans3-Semibold')}
    respaldo_dir = Path(matplotlib.get_data_path())/'fonts'/'ttf'
    respaldo = {'Texto': ('DejaVuSerif', 'DejaVuSerif-Bold', 'DejaVuSerif-Italic', 'DejaVuSerif-Bold'),
                'Titulos': ('DejaVuSans', 'DejaVuSans-Bold', 'DejaVuSans-Oblique', 'DejaVuSans-Bold')}
    usar_propias = all((fuentes/f'{n}.ttf').exists() for nombres in propias.values() for n in nombres)
    for familia in ('Texto', 'Titulos'):
        nombres, carpeta = (propias[familia], fuentes) if usar_propias else (respaldo[familia], respaldo_dir)
        regular, negrita, italica, semi = nombres
        for sufijo, archivo in [('', regular), ('-Negrita', negrita), ('-Italica', italica), ('-Semi', semi)]:
            pdfmetrics.registerFont(TTFont(familia+sufijo, str(carpeta/f'{archivo}.ttf')))
        pdfmetrics.registerFontFamily(familia, normal=familia, bold=familia+'-Negrita',
                                      italic=familia+'-Italica', boldItalic=familia+'-Negrita')
    pdfmetrics.registerFont(TTFont('Mono', str(respaldo_dir/'DejaVuSansMono.ttf')))
    return usar_propias


def estilos():
    """Jerarquía tipográfica del documento."""
    e = {}
    e['texto'] = ParagraphStyle('texto', fontName='Texto', fontSize=10.3, leading=14.1, alignment=TA_JUSTIFY,
                                textColor=TEXTO, spaceAfter=6.5)
    e['lista'] = ParagraphStyle('lista', parent=e['texto'], alignment=TA_LEFT, leftIndent=14, bulletIndent=3, spaceAfter=3.5,
                                bulletFontName='Texto')
    e['capitulo'] = ParagraphStyle('capitulo', fontName='Titulos-Semi', fontSize=18, leading=22, textColor=TINTA,
                                   spaceBefore=0, spaceAfter=4, keepWithNext=1)
    e['seccion'] = ParagraphStyle('seccion', fontName='Titulos-Semi', fontSize=12.6, leading=16, textColor=TINTA,
                                  spaceBefore=11, spaceAfter=5, keepWithNext=1)
    e['subseccion'] = ParagraphStyle('subseccion', fontName='Titulos-Semi', fontSize=10.6, leading=14, textColor=GRIS,
                                     spaceBefore=7, spaceAfter=3, keepWithNext=1)
    e['pie_figura'] = ParagraphStyle('pie_figura', fontName='Titulos', fontSize=8.6, leading=11.4, textColor=GRIS,
                                     alignment=TA_LEFT, spaceBefore=3, spaceAfter=10)
    e['titulo_tabla'] = ParagraphStyle('titulo_tabla', fontName='Titulos', fontSize=8.8, leading=11.6, textColor=GRIS,
                                       spaceBefore=5, spaceAfter=4, keepWithNext=1)
    e['nota_tabla'] = ParagraphStyle('nota_tabla', fontName='Titulos', fontSize=7.8, leading=10, textColor=GRIS_CLARO,
                                     spaceBefore=3, spaceAfter=9)
    e['celda'] = ParagraphStyle('celda', fontName='Titulos', fontSize=8.4, leading=10.4, textColor=TEXTO)
    e['celda_num'] = ParagraphStyle('celda_num', parent=e['celda'], alignment=TA_RIGHT)
    e['cabecera'] = ParagraphStyle('cabecera', fontName='Titulos-Semi', fontSize=8.4, leading=10.4, textColor=TINTA)
    e['cabecera_num'] = ParagraphStyle('cabecera_num', parent=e['cabecera'], alignment=TA_RIGHT)
    e['referencia'] = ParagraphStyle('referencia', parent=e['texto'], fontSize=8.8, leading=11.6, leftIndent=16,
                                     firstLineIndent=-16, alignment=TA_LEFT, spaceAfter=4)
    e['ecuacion_num'] = ParagraphStyle('ecuacion_num', fontName='Texto', fontSize=10.3, leading=14, alignment=TA_RIGHT, textColor=GRIS)
    e['recuadro_titulo'] = ParagraphStyle('recuadro_titulo', fontName='Titulos-Semi', fontSize=10, leading=13, textColor=TINTA, spaceAfter=4)
    # Portada.
    e['portada_titulo'] = ParagraphStyle('portada_titulo', fontName='Titulos-Semi', fontSize=27, leading=33, textColor=TINTA)
    e['portada_sub'] = ParagraphStyle('portada_sub', fontName='Texto', fontSize=13.5, leading=19, textColor=GRIS, spaceBefore=10)
    e['portada_dato'] = ParagraphStyle('portada_dato', fontName='Titulos', fontSize=10.5, leading=15, textColor=TEXTO)
    e['portada_rotulo'] = ParagraphStyle('portada_rotulo', fontName='Titulos-Semi', fontSize=7.8, leading=10, textColor=GRIS_CLARO)
    # Índice.
    e['indice_titulo'] = ParagraphStyle('indice_titulo', parent=e['capitulo'])
    e['toc0'] = ParagraphStyle('toc0', fontName='Titulos-Semi', fontSize=10.3, leading=13.6, textColor=TINTA, spaceBefore=4)
    e['toc1'] = ParagraphStyle('toc1', fontName='Texto', fontSize=9.4, leading=11.8, leftIndent=16, textColor=TEXTO)
    return e


def estilo_tabla(n_filas, n_cols, numericas, resaltar=None):
    """Tabla académica: tres filetes horizontales, sin rejilla vertical."""
    comandos = [
        ('LINEABOVE', (0, 0), (-1, 0), 1.0, TINTA),
        ('LINEBELOW', (0, 0), (-1, 0), 0.6, TINTA),
        ('LINEBELOW', (0, -1), (-1, -1), 1.0, TINTA),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('LEFTPADDING', (0, 0), (-1, -1), 4), ('RIGHTPADDING', (0, 0), (-1, -1), 4),
        ('TOPPADDING', (0, 0), (-1, -1), 3.2), ('BOTTOMPADDING', (0, 0), (-1, -1), 3.2),
    ]
    for i in range(2, n_filas+1, 2):  # sombreado muy suave cada dos filas para seguir la lectura
        comandos.append(('BACKGROUND', (0, i), (-1, i), FONDO_SUAVE))
    if resaltar is not None:
        comandos.append(('LINEBEFORE', (0, resaltar+1), (0, resaltar+1), 2.2, ACENTO))
    return comandos


def encabezado_y_pie(canvas, doc):
    """Encabezado con título corto y capítulo; número de página centrado al pie."""
    canvas.saveState()
    if doc.page > 1:
        y = PAGINA[1]-1.45*cm
        canvas.setFont('Titulos', 8.2)
        canvas.setFillColor(GRIS)
        canvas.drawString(MARGEN['left'], y, 'Pronóstico diario de órdenes de Olist · Módulo B')
        canvas.drawRightString(PAGINA[0]-MARGEN['right'], y, getattr(doc, 'capitulo_actual', ''))
        canvas.setStrokeColor(FILETE); canvas.setLineWidth(.5)
        canvas.line(MARGEN['left'], y-5, PAGINA[0]-MARGEN['right'], y-5)
        canvas.setFont('Titulos', 8.6)
        canvas.drawCentredString(PAGINA[0]/2, 1.25*cm, str(doc.page))
    canvas.setTitle('Pronóstico diario de órdenes de Olist a 28 días')
    canvas.setSubject('Módulo B · Series de tiempo · Taller de Aprendizaje Automático')
    canvas.restoreState()
