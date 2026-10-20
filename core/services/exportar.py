"""
Utilidades compartidas para exportar cualquier listado del panel
(Programas, Jornadas, Fichas, Aprendices, Eventos, Publicaciones...)
a Excel, Word o PDF, sin duplicar la lógica en cada vista.

Los 3 formatos llevan el mismo "membrete" (logo, software, quién
exportó, fecha) y calculan el ancho de cada columna según su
contenido en vez de dejarlo fijo -- así, si en el futuro se agregan
más campos a un listado, el reporte se sigue viendo ordenado sin que
haya que tocar este archivo.

Uso típico dentro de una vista (ya integrado a través de
responder_export, que se encarga de tomar exportado_por de request.user):

    from core.services.exportar import responder_export

    encabezados = ["Nombre", "Código", "Estado"]
    filas = [[p.nombre, p.codigo, p.estado] for p in programas]

    return responder_export(request, "programas", "Programas de formación", encabezados, filas, "usuarios:dashboard")
"""

from io import BytesIO

from django.contrib import messages
from django.contrib.staticfiles import finders
from django.http import HttpResponse
from django.shortcuts import redirect
from django.utils import timezone

NOMBRE_SOFTWARE = "Be Time"
RUTA_LOGO = "img/logo.png"
COLOR_VERDE = "2E8B3D"
COLOR_VERDE_CLARO = "F3F8F0"
COLOR_BORDE = "E1E9DC"
COLOR_GRIS_TEXTO = "666666"


def responder_export(request, nombre_archivo, titulo, encabezados, filas, url_error):
    """
    Decide en qué formato responder (excel/word/pdf) según el parámetro
    ?formato= de la URL. Centraliza lo que antes cada app repetía a mano.

    De aquí sale también "exportado_por": el nombre de quien hizo la
    petición, tomado directo de request.user -- ninguna vista necesita
    pasarlo a mano, ya llega listo a los 3 formatos.

    url_error: nombre de la url (con namespace, ej. "eventos:panel_lista")
    a la que volver si el formato pedido no es válido.
    """
    formato = request.GET.get("formato")

    exportado_por = (
        request.user.get_full_name()
        if request.user.is_authenticated
        else "Usuario no identificado"
    )

    if formato == "excel":
        return exportar_excel(nombre_archivo, titulo, encabezados, filas, exportado_por)
    if formato == "word":
        return exportar_word(nombre_archivo, titulo, encabezados, filas, exportado_por)
    if formato == "pdf":
        return exportar_pdf(nombre_archivo, titulo, encabezados, filas, exportado_por)

    messages.error(request, "Formato de exportación no válido.")
    return redirect(url_error)


def _valor_a_texto(valor):
    if valor is None:
        return ""
    return str(valor)


def _fecha_exportacion():
    return timezone.now().strftime("%d/%m/%Y %H:%M")


def _pesos_de_columna(encabezados, filas, minimo=6, maximo=40):
    """
    Calcula, para cada columna, un "peso" relativo -- pero le da
    mucho más peso al DATO real que al encabezado. El encabezado se
    puede partir en dos líneas (el ajuste de texto está activo en
    los 3 formatos), el dato en general no -- así que un encabezado
    largo con datos cortos (como "Tipo Documento" -> "CC") ya no
    ensancha la columna más de lo que su contenido real necesita;
    el encabezado solo empuja el ancho una fracción de su propio
    largo, y el resto lo resuelve el salto de línea.
    """
    pesos = []
    for i, encabezado in enumerate(encabezados):
        largo_encabezado = len(_valor_a_texto(encabezado))
        largo_datos = max(
            (len(_valor_a_texto(fila[i])) for fila in filas if i < len(fila)),
            default=0,
        )
        peso = max(largo_datos, minimo)
        if largo_encabezado > peso:
            peso = max(peso, largo_encabezado * 0.6)
        pesos.append(min(peso, maximo))
    return pesos


# =========================================================
# Excel
# =========================================================

def exportar_excel(nombre_archivo, titulo, encabezados, filas, exportado_por="Sistema"):
    from openpyxl import Workbook
    from openpyxl.drawing.image import Image as ImagenExcel
    from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
    from openpyxl.utils import get_column_letter
    from openpyxl.worksheet.page import PageMargins

    libro = Workbook()
    hoja = libro.active
    hoja.title = (titulo[:31] or "Datos").strip()

    borde_fino = Border(*(Side(style="thin", color=COLOR_BORDE) for _ in range(4)))

    # ---------- Membrete ----------
    ruta_logo = finders.find(RUTA_LOGO)
    if ruta_logo:
        imagen = ImagenExcel(ruta_logo)
        proporcion = imagen.width / imagen.height
        imagen.height = 50
        imagen.width = 50 * proporcion
        hoja.add_image(imagen, "A1")

    hoja.row_dimensions[1].height = 22
    hoja.append(["", "", NOMBRE_SOFTWARE])
    hoja["C1"].font = Font(bold=True, size=15, color=COLOR_VERDE)

    hoja.append(["", "", titulo])
    hoja["C2"].font = Font(bold=True, size=12)

    hoja.append(["", "", f"Exportado por: {exportado_por}   |   Fecha: {_fecha_exportacion()}   |   Total de registros: {len(filas)}"])
    hoja["C3"].font = Font(size=9, italic=True, color=COLOR_GRIS_TEXTO)

    hoja.append([])  # separación

    # ---------- Tabla de datos ----------
    # Importante: fila_encabezados se calcula DESPUÉS de escribir la
    # fila, no antes -- un append() con una fila vacía (la de arriba,
    # de separación) no siempre actualiza max_row en openpyxl, así
    # que calcularlo antes podía apuntar a la fila equivocada (la de
    # separación) y dejar los encabezados con la altura por defecto,
    # cortando el texto cuando necesitaba partirse en 2 líneas.
    hoja.append(encabezados)
    fila_encabezados = hoja.max_row
    hoja.row_dimensions[fila_encabezados].height = 32
    for celda in hoja[fila_encabezados]:
        celda.font = Font(bold=True, color="FFFFFF", size=10)
        celda.fill = PatternFill(start_color=COLOR_VERDE, end_color=COLOR_VERDE, fill_type="solid")
        celda.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        celda.border = borde_fino

    for indice_fila, fila in enumerate(filas):
        hoja.append([_valor_a_texto(v) for v in fila])
        fila_actual = hoja.max_row
        relleno_zebra = PatternFill(
            start_color=COLOR_VERDE_CLARO, end_color=COLOR_VERDE_CLARO, fill_type="solid"
        ) if indice_fila % 2 == 1 else None
        for celda in hoja[fila_actual]:
            celda.border = borde_fino
            celda.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
            if relleno_zebra:
                celda.fill = relleno_zebra

    # ---------- Anchos de columna, según contenido ----------
    pesos = _pesos_de_columna(encabezados, filas)
    for i, peso in enumerate(pesos, start=1):
        hoja.column_dimensions[get_column_letter(i)].width = peso + 5

    # ---------- Encabezados fijos al desplazar, y filtro rápido ----------
    hoja.freeze_panes = f"A{fila_encabezados + 1}"
    hoja.auto_filter.ref = f"A{fila_encabezados}:{get_column_letter(len(encabezados))}{hoja.max_row}"

    # ---------- Que se imprima bien: horizontal, ajustado al ancho, con el encabezado repetido ----------
    from openpyxl.worksheet.properties import PageSetupProperties

    hoja.page_setup.orientation = "landscape"
    hoja.page_setup.fitToWidth = 1
    hoja.page_setup.fitToHeight = 0
    hoja.sheet_properties.pageSetUpPr = PageSetupProperties(fitToPage=True)
    hoja.print_title_rows = f"{fila_encabezados}:{fila_encabezados}"
    hoja.page_margins = PageMargins(left=0.4, right=0.4, top=0.5, bottom=0.5)

    buffer = BytesIO()
    libro.save(buffer)
    buffer.seek(0)

    response = HttpResponse(
        buffer.read(),
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    response["Content-Disposition"] = f'attachment; filename="{nombre_archivo}.xlsx"'
    return response


# =========================================================
# Word
# =========================================================

def _repetir_fila_como_encabezado(fila_tabla):
    """
    Word no tiene, en python-docx, una propiedad directa para "repetir
    esta fila en cada página" -- hay que pedírselo al XML interno del
    documento a mano. Esto hace que, si la tabla ocupa varias hojas,
    el encabezado no desaparezca después de la primera.
    """
    from docx.oxml import OxmlElement
    from docx.oxml.ns import qn

    propiedades_fila = fila_tabla._tr.get_or_add_trPr()
    encabezado_repetido = OxmlElement("w:tblHeader")
    encabezado_repetido.set(qn("w:val"), "true")
    propiedades_fila.append(encabezado_repetido)


def _agregar_cuadricula(tabla, color_borde):
    """
    Igual que con "repetir encabezado": Word no expone en python-docx
    una forma directa de ponerle línea a cada celda de una tabla, así
    que se arma el bloque de bordes a mano en el XML y se le pega a
    las propiedades de la tabla completa (tblBorders), en vez de
    tener que repetirlo celda por celda.
    """
    from docx.oxml import OxmlElement
    from docx.oxml.ns import qn

    propiedades_tabla = tabla._tbl.tblPr
    bordes = OxmlElement("w:tblBorders")
    for nombre in ("top", "left", "bottom", "right", "insideH", "insideV"):
        borde = OxmlElement(f"w:{nombre}")
        borde.set(qn("w:val"), "single")
        borde.set(qn("w:sz"), "4")
        borde.set(qn("w:space"), "0")
        borde.set(qn("w:color"), color_borde)
        bordes.append(borde)
    propiedades_tabla.append(bordes)


def exportar_word(nombre_archivo, titulo, encabezados, filas, exportado_por="Sistema"):
    from docx import Document
    from docx.enum.section import WD_ORIENT
    from docx.enum.table import WD_TABLE_ALIGNMENT
    from docx.enum.text import WD_ALIGN_PARAGRAPH
    from docx.oxml import OxmlElement
    from docx.oxml.ns import qn
    from docx.shared import Inches, Pt, RGBColor

    documento = Document()

    # ---------- Hoja horizontal, con márgenes angostos para más espacio útil ----------
    seccion = documento.sections[0]
    seccion.orientation = WD_ORIENT.LANDSCAPE
    seccion.page_width, seccion.page_height = seccion.page_height, seccion.page_width
    seccion.left_margin = Inches(0.5)
    seccion.right_margin = Inches(0.5)
    seccion.top_margin = Inches(0.6)
    seccion.bottom_margin = Inches(0.5)

    # ---------- Membrete (en el header: se repite en cada página sola) ----------
    encabezado = seccion.header
    parrafo = encabezado.paragraphs[0]

    ruta_logo = finders.find(RUTA_LOGO)
    if ruta_logo:
        run_logo = parrafo.add_run()
        run_logo.add_picture(ruta_logo, height=Inches(0.35))
        parrafo.add_run("   ")

    run_software = parrafo.add_run(NOMBRE_SOFTWARE)
    run_software.font.bold = True
    run_software.font.size = Pt(13)
    run_software.font.color.rgb = RGBColor.from_string(COLOR_VERDE)

    parrafo_info = encabezado.add_paragraph()
    run_info = parrafo_info.add_run(
        f"Exportado por: {exportado_por}   |   Fecha: {_fecha_exportacion()}   |   Total de registros: {len(filas)}"
    )
    run_info.font.size = Pt(8)
    run_info.font.italic = True
    run_info.font.color.rgb = RGBColor.from_string(COLOR_GRIS_TEXTO)

    # ---------- Título ----------
    encabezado_titulo = documento.add_heading(titulo, level=1)
    for run in encabezado_titulo.runs:
        run.font.color.rgb = RGBColor.from_string(COLOR_VERDE)

    # ---------- Tabla ----------
    tabla = documento.add_table(rows=1, cols=len(encabezados))
    tabla.alignment = WD_TABLE_ALIGNMENT.CENTER
    tabla.autofit = False

    _repetir_fila_como_encabezado(tabla.rows[0])
    _agregar_cuadricula(tabla, COLOR_BORDE)

    celdas_encabezado = tabla.rows[0].cells
    for i, encabezado_col in enumerate(encabezados):
        celda = celdas_encabezado[i]
        celda.text = encabezado_col

        sombreado = OxmlElement("w:shd")
        sombreado.set(qn("w:fill"), COLOR_VERDE)
        celda._tc.get_or_add_tcPr().append(sombreado)

        for parrafo_celda in celda.paragraphs:
            parrafo_celda.alignment = WD_ALIGN_PARAGRAPH.CENTER
            for run in parrafo_celda.runs:
                run.font.bold = True
                run.font.size = Pt(9)
                run.font.color.rgb = RGBColor.from_string("FFFFFF")

    for indice_fila, fila in enumerate(filas):
        celdas = tabla.add_row().cells
        es_par = indice_fila % 2 == 1
        for i, valor in enumerate(fila):
            celda = celdas[i]
            celda.text = _valor_a_texto(valor)

            if es_par:
                sombreado = OxmlElement("w:shd")
                sombreado.set(qn("w:fill"), COLOR_VERDE_CLARO)
                celda._tc.get_or_add_tcPr().append(sombreado)

            for parrafo_celda in celda.paragraphs:
                parrafo_celda.alignment = WD_ALIGN_PARAGRAPH.CENTER
                for run in parrafo_celda.runs:
                    run.font.size = Pt(9)

    # ---------- Ancho de columnas, repartido según el contenido ----------
    pesos = _pesos_de_columna(encabezados, filas)
    total_peso = sum(pesos) or 1
    ancho_disponible = seccion.page_width - seccion.left_margin - seccion.right_margin

    for i, peso in enumerate(pesos):
        ancho_columna = int(ancho_disponible * peso / total_peso)
        for fila_tabla in tabla.rows:
            fila_tabla.cells[i].width = ancho_columna

    # ---------- Pie con el total (además del que ya va en el encabezado) ----------
    parrafo_final = documento.add_paragraph()
    run_final = parrafo_final.add_run(f"Total de registros: {len(filas)}")
    run_final.font.size = Pt(9)
    run_final.font.italic = True
    run_final.font.color.rgb = RGBColor.from_string(COLOR_GRIS_TEXTO)

    buffer = BytesIO()
    documento.save(buffer)
    buffer.seek(0)

    response = HttpResponse(
        buffer.read(),
        content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    )
    response["Content-Disposition"] = f'attachment; filename="{nombre_archivo}.docx"'
    return response


# =========================================================
# PDF
# =========================================================

def exportar_pdf(nombre_archivo, titulo, encabezados, filas, exportado_por="Sistema"):
    from reportlab.lib import colors
    from reportlab.lib.enums import TA_CENTER
    from reportlab.lib.pagesizes import landscape, letter
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.lib.units import inch
    from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

    ruta_logo = finders.find(RUTA_LOGO)
    fecha_exportacion = _fecha_exportacion()
    total_registros = len(filas)
    margen_lateral = 0.4 * inch

    def dibujar_membrete(canvas_obj, doc):
        """
        Reportlab dibuja esto directo sobre cada página (no es parte
        del contenido normal) -- por eso el logo y el texto del
        membrete aparecen en TODAS las hojas del PDF, no solo la
        primera. También se aprovecha para numerar las páginas.
        """
        canvas_obj.saveState()
        ancho_pagina, alto_pagina = landscape(letter)

        if ruta_logo:
            canvas_obj.drawImage(
                ruta_logo,
                margen_lateral, alto_pagina - 0.55 * inch,
                width=1.1 * inch, height=1.1 * inch / 2.594,
                preserveAspectRatio=True, mask="auto",
            )

        canvas_obj.setFont("Helvetica-Bold", 12)
        canvas_obj.setFillColor(colors.HexColor(f"#{COLOR_VERDE}"))
        canvas_obj.drawString(margen_lateral + 1.3 * inch, alto_pagina - 0.35 * inch, NOMBRE_SOFTWARE)

        canvas_obj.setFont("Helvetica", 8)
        canvas_obj.setFillColor(colors.HexColor(f"#{COLOR_GRIS_TEXTO}"))
        canvas_obj.drawString(
            margen_lateral + 1.3 * inch, alto_pagina - 0.5 * inch,
            f"Exportado por: {exportado_por}   |   Fecha: {fecha_exportacion}   |   Total: {total_registros} registros"
        )

        # Línea separadora bajo el membrete
        canvas_obj.setStrokeColor(colors.HexColor(f"#{COLOR_BORDE}"))
        canvas_obj.line(margen_lateral, alto_pagina - 0.65 * inch, ancho_pagina - margen_lateral, alto_pagina - 0.65 * inch)

        # Pie de página con el número de hoja
        canvas_obj.setFont("Helvetica", 7)
        canvas_obj.setFillColor(colors.HexColor(f"#{COLOR_GRIS_TEXTO}"))
        canvas_obj.drawRightString(ancho_pagina - margen_lateral, 0.3 * inch, f"Página {doc.page}")

        canvas_obj.restoreState()

    buffer = BytesIO()
    documento = SimpleDocTemplate(
        buffer,
        pagesize=landscape(letter),
        topMargin=0.9 * inch,
        bottomMargin=0.5 * inch,
        leftMargin=margen_lateral,
        rightMargin=margen_lateral,
    )
    estilos = getSampleStyleSheet()

    elementos = [
        Paragraph(titulo, estilos["Title"]),
        Spacer(1, 10),
    ]

    # ---------- Ancho de columnas: reparte TODO el ancho disponible
    # según qué tan largo es el contenido de cada una, en vez de
    # dejar la tabla más angosta que la hoja. ----------
    ancho_disponible = landscape(letter)[0] - documento.leftMargin - documento.rightMargin
    pesos = _pesos_de_columna(encabezados, filas)
    total_peso = sum(pesos) or 1
    anchos_columnas = [ancho_disponible * peso / total_peso for peso in pesos]

    # ---------- Celdas como Paragraph, no texto plano ----------
    # reportlab no ajusta línea por sí solo en una celda de texto
    # plano -- con columnas ahora más ajustadas al contenido real
    # (ver _pesos_de_columna), un encabezado o dato que no quepa en
    # una sola línea necesita poder partirse en dos, en vez de
    # desbordarse fuera de la celda.
    estilo_encabezado_celda = ParagraphStyle(
        "encabezado_celda", fontName="Helvetica-Bold", fontSize=8,
        textColor=colors.white, alignment=TA_CENTER, leading=10,
    )
    estilo_dato_celda = ParagraphStyle(
        "dato_celda", fontName="Helvetica", fontSize=7.5,
        textColor=colors.HexColor("#1a1a1a"), alignment=TA_CENTER, leading=9,
    )

    fila_encabezados_pdf = [Paragraph(_valor_a_texto(h), estilo_encabezado_celda) for h in encabezados]
    datos_tabla = [fila_encabezados_pdf] + [
        [Paragraph(_valor_a_texto(v), estilo_dato_celda) for v in fila]
        for fila in filas
    ]

    tabla = Table(datos_tabla, colWidths=anchos_columnas, repeatRows=1)
    tabla.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor(f"#{COLOR_VERDE}")),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor(f"#{COLOR_BORDE}")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor(f"#{COLOR_VERDE_CLARO}")]),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    elementos.append(tabla)

    documento.build(elementos, onFirstPage=dibujar_membrete, onLaterPages=dibujar_membrete)
    buffer.seek(0)

    response = HttpResponse(buffer.read(), content_type="application/pdf")
    response["Content-Disposition"] = f'attachment; filename="{nombre_archivo}.pdf"'
    return response
