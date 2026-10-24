"""Convierte la fuente del informe (fuente.md) en PDF y en Markdown.

Sintaxis de la fuente (además de #, ##, ###, párrafos, listas con '- ',
**negrita**, *cursiva* y `código`):
  {{clave}}                         valor de contexto.py
  ::: figura archivo | alto_cm | pie   figura de documentacion/figuras/
  ::: tabla clave | título | nota      tabla de contexto.py
  ::: ecuacion clave | expresión       ecuación numerada (mathtext de matplotlib)
  ::: referencia texto              entrada bibliográfica
  ::: portada / ::: indice / ::: recuadro título ... ::: fin / ::: anexos / ::: salto
  [[fig:archivo]] [[tab:clave]] [[ec:clave]]   referencias cruzadas numeradas
"""
import re
import tempfile
from pathlib import Path
from xml.sax.saxutils import escape
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from reportlab.lib.units import cm
from reportlab.platypus import (BaseDocTemplate, PageTemplate, Frame, Paragraph, Spacer, Table, Image,
                                PageBreak, KeepTogether, CondPageBreak)
from reportlab.platypus.flowables import HRFlowable
from reportlab.platypus.tableofcontents import TableOfContents
from src.configuracion import ROOT
from . import diseno
from .contexto import construir

FUENTE = Path(__file__).with_name('fuente.md')
DOC = ROOT/'documentacion'
# Solo se resuelve el módulo de series de tiempo: el documento completo, anexos
# incluidos, se limita a 20 páginas (el enunciado fija 20 sin anexos para tres módulos).
LIMITE_TOTAL = 20


# --------------------------------------------------------------------------
# Lectura de la fuente
# --------------------------------------------------------------------------
def sustituir(texto, valores):
    texto = re.sub(r'<!--.*?-->', '', texto, flags=re.S)  # los comentarios no se publican
    faltan = sorted(set(re.findall(r'\{\{(\w+)\}\}', texto)) - set(valores))
    if faltan:
        raise KeyError(f'Marcadores sin valor en contexto.py: {faltan}')
    return re.sub(r'\{\{(\w+)\}\}', lambda m: valores[m.group(1)], texto)


def bloques(texto):
    """Agrupa la fuente en bloques (tipo, contenido)."""
    salida, parrafo, lista = [], [], []
    def cerrar():
        if parrafo:
            salida.append(('p', ' '.join(parrafo))); parrafo.clear()
        if lista:
            salida.append(('l', list(lista))); lista.clear()
    for linea in texto.splitlines():
        s = linea.strip()
        if s.startswith('<!--'):
            continue
        if not s:
            cerrar(); continue
        if s.startswith(':::'):
            cerrar()
            nombre, _, resto = s[3:].strip().partition(' ')
            if nombre == 'ecuacion':
                clave, _, expresion = resto.partition('|')
                salida.append((nombre, [clave.strip(), expresion.strip()]))
            else:
                salida.append((nombre, [x.strip() for x in resto.split('|')] if resto else []))
        elif s.startswith('### '):
            cerrar(); salida.append(('h3', s[4:]))
        elif s.startswith('## '):
            cerrar(); salida.append(('h2', s[3:]))
        elif s.startswith('# '):
            cerrar(); salida.append(('h1', s[2:]))
        elif s.startswith('- '):
            if parrafo:
                cerrar()
            lista.append(s[2:])
        elif lista and linea.startswith('  '):
            lista[-1] += ' ' + s
        else:
            parrafo.append(s)
    cerrar()
    return salida


def numerar(bs):
    """Numera figuras, tablas y ecuaciones en orden de aparición."""
    n = {'figura': 0, 'tabla': 0, 'ecuacion': 0}
    ref = {}
    for tipo, cont in bs:
        if tipo in n:
            n[tipo] += 1
            prefijo = {'figura': 'fig', 'tabla': 'tab', 'ecuacion': 'ec'}[tipo]
            ref[f'{prefijo}:{cont[0]}'] = n[tipo]
    return ref


def resolver(texto, ref):
    def cambio(m):
        clave = m.group(1)
        if clave not in ref:
            raise KeyError(f'Referencia cruzada sin destino: {clave}')
        tipo = clave.split(':')[0]
        return {'fig': f'Figura {ref[clave]}', 'tab': f'Tabla {ref[clave]}', 'ec': f'({ref[clave]})'}[tipo]
    return re.sub(r'\[\[([a-z]+:[\w]+)\]\]', cambio, texto)


# --------------------------------------------------------------------------
# PDF
# --------------------------------------------------------------------------
MACROS = [(r'\hat{y}', 'ŷ'), (r'\bar{y}', 'ȳ'), (r'\log', 'log'), (r'\ln', 'ln'), (r'\exp', 'exp'),
          (r'\dots', '…'), (r'\beta', 'β'), (r'\alpha', 'α'), (r'\pm', '±'), (r'\,', ' ')]


def matematica(m):
    """Notación en línea ($...$) a texto tipográfico: cursiva, subíndices y superíndices."""
    for a, b in MACROS:
        m = m.replace(a, b)
    m = m.replace('-', '−')
    m = re.sub(r'\^\{([^}]*)\}', r'<super>\1</super>', m)
    m = re.sub(r'_\{([^}]*)\}', r'<sub>\1</sub>', m)
    m = re.sub(r'_([\w+−]+)', r'<sub>\1</sub>', m)
    m = re.sub(r'\^(\w)', r'<super>\1</super>', m)
    return f'<i>{m}</i>'


def rico(t):
    """Escapa y convierte el marcado ligero (negrita, cursiva, código y $matemática$) al de ReportLab."""
    t = escape(t)
    t = re.sub(r'\$(.+?)\$', lambda m: matematica(m.group(1)), t)
    t = re.sub(r'`(.+?)`', r'<font face="Mono" size="8.6">\1</font>', t)
    t = re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', t)
    t = re.sub(r'(?<![\w*])\*(?!\s)(.+?)(?<!\s)\*(?![\w*])', r'<i>\1</i>', t)
    return t


def ecuacion_png(expresion, carpeta, i):
    archivo = carpeta/f'ecuacion_{i}.png'
    fig = plt.figure(figsize=(0.01, 0.01))
    fig.text(0, 0, f'${expresion}$', fontsize=12.5, math_fontfamily='stix')
    fig.savefig(archivo, dpi=300, bbox_inches='tight', pad_inches=0.04, transparent=True)
    plt.close(fig)
    return archivo


def tabla_pdf(df, numericas, resaltar, e, ancho=None):
    columnas = list(df.columns)
    longitudes = []
    for c in columnas:
        celdas = [len(str(v)) for v in df[c]]
        longitudes.append(max(max(celdas) if celdas else 0, min(len(c), 18)) + 2)
    total = sum(longitudes)
    anchos = [max(.08, l/total) for l in longitudes]
    anchos = [(ancho or diseno.ANCHO)*a/sum(anchos) for a in anchos]
    filas = [[Paragraph(rico(c), e['cabecera_num' if c in numericas else 'cabecera']) for c in columnas]]
    for _, fila in df.iterrows():
        filas.append([Paragraph(rico(str(fila[c])), e['celda_num' if c in numericas else 'celda']) for c in columnas])
    t = Table(filas, colWidths=anchos, repeatRows=1, hAlign='LEFT')
    t.setStyle(diseno.estilo_tabla(len(df), len(columnas), numericas, resaltar))
    return t


class Informe(BaseDocTemplate):
    """Registra capítulos para el encabezado, el índice, los marcadores del PDF y el inicio de los anexos."""
    def __init__(self, archivo, **kw):
        super().__init__(archivo, pagesize=diseno.PAGINA, leftMargin=diseno.MARGEN['left'],
                         rightMargin=diseno.MARGEN['right'], topMargin=diseno.MARGEN['top'],
                         bottomMargin=diseno.MARGEN['bottom'], **kw)
        marco = Frame(self.leftMargin, self.bottomMargin, self.width, self.height, id='cuerpo',
                      leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0)
        self.addPageTemplates([PageTemplate(id='pagina', frames=[marco], onPageEnd=diseno.encabezado_y_pie)])
        self.capitulo_actual, self.pagina_anexos, self.n_marca = '', None, 0

    def beforeDocument(self):
        # multiBuild compone varias pasadas: las claves deben repetirse para que el índice converja.
        self.capitulo_actual, self.pagina_anexos, self.n_marca = '', None, 0

    def afterFlowable(self, f):
        if not isinstance(f, Paragraph):
            return
        estilo = f.style.name
        texto = f.getPlainText()
        if estilo in ('capitulo', 'seccion'):
            nivel = 0 if estilo == 'capitulo' else 1
            if estilo == 'capitulo':
                self.capitulo_actual = texto
                if texto.startswith('Anexos') and self.pagina_anexos is None:
                    self.pagina_anexos = self.page
            self.n_marca += 1
            clave = f'm{self.n_marca}'
            self.canv.bookmarkPage(clave)
            self.canv.addOutlineEntry(texto, clave, level=nivel, closed=nivel > 0)
            self.notify('TOCEntry', (nivel, texto, self.page, clave))


def construir_pdf(bs, valores, tablas, ref, e, salida):
    historia, n_fig, n_tab, n_ec = [], 0, 0, 0
    tmp = Path(tempfile.mkdtemp(prefix='ecuaciones_'))
    pila = []           # contenido de un recuadro en construcción
    destino = historia
    sin_salto = False   # el primer anexo comparte página con el título 'Anexos'
    for tipo, cont in bs:
        if tipo == 'portada':
            datos = dict(x.split(':', 1) for x in cont)
            destino += [Spacer(1, 4.2*cm),
                        Paragraph(rico(datos['rotulo'].strip()), e['portada_rotulo']), Spacer(1, 10),
                        Paragraph(rico(datos['titulo'].strip()), e['portada_titulo']),
                        Paragraph(rico(datos['subtitulo'].strip()), e['portada_sub']), Spacer(1, 1.2*cm),
                        HRFlowable(width='38%', thickness=1.4, color=diseno.ACENTO, hAlign='LEFT', spaceAfter=1.4*cm)]
            for etiqueta in ('Autores', 'Profesor', 'Curso', 'Programa', 'Institución', 'Fecha'):
                if etiqueta.lower() in {k.strip().lower() for k in datos}:
                    valor = next(v for k, v in datos.items() if k.strip().lower() == etiqueta.lower())
                    destino += [Paragraph(etiqueta.upper(), e['portada_rotulo']),
                                Paragraph(rico(valor.strip()), e['portada_dato']), Spacer(1, 9)]
            destino.append(PageBreak())
        elif tipo == 'indice':
            toc = TableOfContents(dotsMinLevel=0)
            toc.levelStyles = [e['toc0'], e['toc1']]
            destino += [Paragraph('Índice', e['indice_titulo']), HRFlowable(width='100%', thickness=.6, color=diseno.FILETE, spaceAfter=10), toc]
        elif tipo == 'h1':
            # Un capítulo abre página solo si queda poco espacio; los saltos obligados
            # (índice, resumen ejecutivo de una página) se marcan con ::: salto en la fuente.
            if not sin_salto:
                destino += [Spacer(1, 10), CondPageBreak(10*cm)]
            sin_salto = False
            m = re.match(r'^(\d+\.|Anexo [A-Z]\.)\s*(.*)$', cont)
            titulo = f'<font color="#8A8984">{rico(m.group(1))}</font>&nbsp;&nbsp;{rico(m.group(2))}' if m else rico(cont)
            destino += [Paragraph(titulo, e['capitulo']), HRFlowable(width='100%', thickness=.8, color=diseno.TINTA, spaceBefore=2, spaceAfter=12)]
        elif tipo == 'h2':
            destino += [CondPageBreak(3.2*cm), Paragraph(rico(cont), e['seccion'])]
        elif tipo == 'h3':
            destino.append(Paragraph(rico(cont), e['subseccion']))
        elif tipo == 'p':
            destino.append(Paragraph(rico(cont), e['texto']))
        elif tipo == 'l':
            destino += [Paragraph(rico(x), e['lista'], bulletText='•') for x in cont]
        elif tipo == 'figura':
            archivo, alto, pie = cont[0], float(cont[1]), cont[2]
            n_fig += 1
            ruta = DOC/'figuras'/f'{archivo}.png'
            if not ruta.exists():
                raise FileNotFoundError(ruta)
            im = Image(str(ruta))
            escala = min(diseno.ANCHO/im.imageWidth, alto*cm/im.imageHeight)
            im.drawWidth, im.drawHeight = im.imageWidth*escala, im.imageHeight*escala
            im.hAlign = 'CENTER'
            destino.append(KeepTogether([Spacer(1, 4), im,
                Paragraph(f'<font name="Titulos-Semi" color="#1F3A5F">Figura {n_fig}.</font> {rico(pie)}', e['pie_figura'])]))
        elif tipo == 'tabla':
            clave, titulo = cont[0], cont[1]
            nota = cont[2] if len(cont) > 2 else ''
            n_tab += 1
            df, numericas, resaltar = tablas[clave]
            partes = [Paragraph(f'<font name="Titulos-Semi" color="#1F3A5F">Tabla {n_tab}.</font> {rico(titulo)}', e['titulo_tabla']),
                      tabla_pdf(df, numericas, resaltar, e, ancho=diseno.ANCHO-24 if destino is pila else None)]
            if nota:
                partes.append(Paragraph(rico(nota), e['nota_tabla']))
            else:
                partes.append(Spacer(1, 9))
            # Dentro del recuadro no se usa KeepTogether: la caja ya mantiene unido su contenido.
            if destino is pila:
                destino.extend(partes)
            else:
                destino.append(KeepTogether(partes))
        elif tipo == 'ecuacion':
            n_ec += 1
            png = ecuacion_png(cont[1], tmp, n_ec)
            im = Image(str(png))
            # La imagen se renderiza a 300 ppp: 72/300 la devuelve a su tamaño tipográfico.
            escala = min(72/300, (diseno.ANCHO-2*cm)/im.imageWidth)
            im.drawWidth, im.drawHeight = im.imageWidth*escala, im.imageHeight*escala
            fila = Table([[im, Paragraph(f'({n_ec})', e['ecuacion_num'])]], colWidths=[diseno.ANCHO-1.4*cm, 1.4*cm])
            fila.setStyle([('VALIGN', (0, 0), (-1, -1), 'MIDDLE'), ('ALIGN', (0, 0), (0, 0), 'CENTER'),
                           ('TOPPADDING', (0, 0), (-1, -1), 2), ('BOTTOMPADDING', (0, 0), (-1, -1), 6)])
            destino.append(fila)
        elif tipo == 'referencia':
            destino.append(Paragraph(rico(cont[0]), e['referencia']))
        elif tipo == 'recuadro':
            pila = [Paragraph(rico(cont[0]), e['recuadro_titulo'])] if cont else []
            destino = pila
        elif tipo == 'fin':
            caja = Table([[pila]], colWidths=[diseno.ANCHO])
            caja.setStyle([('BOX', (0, 0), (-1, -1), .8, diseno.TINTA), ('BACKGROUND', (0, 0), (-1, -1), diseno.FONDO_SUAVE),
                           ('LEFTPADDING', (0, 0), (-1, -1), 11), ('RIGHTPADDING', (0, 0), (-1, -1), 11),
                           ('TOPPADDING', (0, 0), (-1, -1), 9), ('BOTTOMPADDING', (0, 0), (-1, -1), 6)])
            destino = historia
            destino += [caja, Spacer(1, 10)]
        elif tipo == 'salto':
            destino.append(PageBreak())
        elif tipo == 'anexos':
            destino += [PageBreak(), Paragraph('Anexos', e['capitulo']),
                        HRFlowable(width='100%', thickness=.8, color=diseno.TINTA, spaceBefore=2, spaceAfter=12)]
            sin_salto = True
        else:
            raise ValueError(f'Directiva desconocida: {tipo}')
    doc = Informe(str(salida))
    doc.multiBuild(historia)
    return doc


# --------------------------------------------------------------------------
# Markdown para GitHub
# --------------------------------------------------------------------------
def markdown(bs, tablas, ref):
    md, n_fig, n_tab, n_ec = [], 0, 0, 0
    for tipo, cont in bs:
        if tipo == 'portada':
            datos = dict(x.split(':', 1) for x in cont)
            md += [f'# {datos["titulo"].strip()}', '', f'*{datos["subtitulo"].strip()}*', '']
            for etiqueta in ('Autores', 'Profesor', 'Curso', 'Programa', 'Institución', 'Fecha'):
                valor = datos.get(etiqueta)
                if valor:
                    md += [f'**{etiqueta}:** {valor.strip()}  ']
            md += ['']
        elif tipo == 'h1':
            md += [f'## {cont}', '']
        elif tipo == 'h2':
            md += [f'### {cont}', '']
        elif tipo == 'h3':
            md += [f'#### {cont}', '']
        elif tipo == 'p':
            md += [cont, '']
        elif tipo == 'l':
            md += [f'- {x}' for x in cont] + ['']
        elif tipo == 'figura':
            n_fig += 1
            md += [f'![Figura {n_fig}](figuras/{cont[0]}.png)', '', f'*Figura {n_fig}. {cont[2]}*', '']
        elif tipo == 'tabla':
            n_tab += 1
            df = tablas[cont[0]][0]
            md += [f'**Tabla {n_tab}. {cont[1]}**', '', '| ' + ' | '.join(df.columns) + ' |',
                   '| ' + ' | '.join('---' for _ in df.columns) + ' |']
            md += ['| ' + ' | '.join(str(v).replace('|', '/') for v in fila) + ' |' for fila in df.itertuples(index=False)]
            md += ([''] + [f'*{cont[2]}*'] if len(cont) > 2 else []) + ['']
        elif tipo == 'ecuacion':
            n_ec += 1
            md += [f'$$ {cont[1]} \\qquad ({n_ec}) $$', '']
        elif tipo == 'referencia':
            md += [f'- {cont[0]}']
        elif tipo == 'recuadro':
            md += [f'> **{cont[0]}**' if cont else '>', '']
        elif tipo == 'anexos':
            md += ['', '## Anexos', '']
    return '\n'.join(md) + '\n'


def generar():
    diseno.registrar_fuentes()
    e = diseno.estilos()
    valores, tablas = construir()
    texto = sustituir(FUENTE.read_text(encoding='utf-8'), valores)
    bs = bloques(texto)
    ref = numerar(bs)
    bs = [(tipo, resolver(cont, ref) if isinstance(cont, str) else
           [resolver(x, ref) for x in cont] if isinstance(cont, list) and cont and isinstance(cont[0], str) else cont)
          for tipo, cont in bs]
    for tipo, cont in bs:
        if tipo == 'tabla' and cont[0] not in tablas:
            raise KeyError(f'Tabla sin datos en contexto.py: {cont[0]}')
    doc = construir_pdf(bs, valores, tablas, ref, e, DOC/'informe.pdf')
    (DOC/'informe.md').write_text(markdown(bs, tablas, ref), encoding='utf-8')
    cuerpo = (doc.pagina_anexos or doc.page+1) - 1
    print(f'Informe PDF: {doc.page} páginas en total (límite {LIMITE_TOTAL}); cuerpo {cuerpo}, anexos desde la página {doc.pagina_anexos}.')
    if doc.page > LIMITE_TOTAL:
        raise RuntimeError(f'El informe tiene {doc.page} páginas; el límite total es {LIMITE_TOTAL}.')
    return doc
