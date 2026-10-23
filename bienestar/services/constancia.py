"""
Constancia de horas de bienestar: emisión (registro verificable) y PDF.
"""

from io import BytesIO

from django.contrib.staticfiles import finders
from django.utils import timezone

from bienestar.models import ConstanciaHoras
from bienestar.services.progreso import calcular_progreso, horas_de, total_horas_de

NOMBRE_SOFTWARE = "Be Time"
COLOR_VERDE = "#2E8B3D"
COLOR_BORDE = "#E1E9DC"
COLOR_GRIS = "#666666"
RUTA_LOGO = "img/logo.png"


class SinHorasError(Exception):
    """El aprendiz todavía no tiene horas de bienestar para certificar."""


def emitir_constancia(aprendiz):
    """
    Crea (o reutiliza) el registro de la constancia del aprendiz con sus horas de hoy.

    Si ya emitió una el mismo día con exactamente las mismas horas, se
    devuelve esa misma (mismo código): descargar el PDF diez veces no
    llena la tabla de registros ni genera diez códigos distintos.
    """
    total = total_horas_de(aprendiz)
    if total <= 0:
        raise SinHorasError("Todavía no tienes horas de bienestar registradas.")

    hoy = timezone.localdate()
    existente = next(
        (c for c in aprendiz.constancias.all()
         if c.total_horas == total and timezone.localtime(c.fecha_emision).date() == hoy),
        None,
    )
    if existente:
        return existente

    usuario = aprendiz.usuario
    grupo = aprendiz.grupo
    return ConstanciaHoras.objects.create(
        aprendiz=aprendiz,
        nombre=usuario.get_full_name(),
        tipo_documento=usuario.tipo_documento,
        numero_documento=usuario.numero_documento,
        programa=grupo.programa_formacion.nombre,
        grupo=grupo.numero_grupo,
        total_horas=total,
        meta_horas=calcular_progreso(total)["meta"],
    )


def _qr_imagen(url):
    from eventos.services.qr import generar_imagen_qr
    return generar_imagen_qr(url)


def generar_pdf_constancia(constancia, url_verificacion):
    """Devuelve los bytes del PDF de la constancia (hoja carta vertical)."""
    from reportlab.lib import colors
    from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY
    from reportlab.lib.pagesizes import letter
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.lib.units import inch
    from reportlab.platypus import (
        Image, KeepTogether, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle,
    )
    from xml.sax.saxutils import escape

    aprendiz = constancia.aprendiz
    fecha = timezone.localtime(constancia.fecha_emision)
    meses = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio",
             "agosto", "septiembre", "octubre", "noviembre", "diciembre"]
    fecha_texto = f"{fecha.day} de {meses[fecha.month - 1]} de {fecha.year}"

    ruta_logo = finders.find(RUTA_LOGO)

    def membrete(canvas_obj, doc):
        canvas_obj.saveState()
        ancho, alto = letter
        if ruta_logo:
            canvas_obj.drawImage(ruta_logo, 0.8 * inch, alto - 0.95 * inch,
                                 width=1.2 * inch, height=1.2 * inch / 2.594,
                                 preserveAspectRatio=True, mask="auto")
        canvas_obj.setFont("Helvetica-Bold", 13)
        canvas_obj.setFillColor(colors.HexColor(COLOR_VERDE))
        canvas_obj.drawString(2.3 * inch, alto - 0.65 * inch, NOMBRE_SOFTWARE)
        canvas_obj.setFont("Helvetica", 9)
        canvas_obj.setFillColor(colors.HexColor(COLOR_GRIS))
        canvas_obj.drawString(2.3 * inch, alto - 0.82 * inch,
                              "Bienestar al Aprendiz - Servicio Nacional de Aprendizaje SENA")
        canvas_obj.setStrokeColor(colors.HexColor(COLOR_BORDE))
        canvas_obj.line(0.8 * inch, alto - 1.1 * inch, ancho - 0.8 * inch, alto - 1.1 * inch)
        canvas_obj.setFont("Helvetica", 7.5)
        canvas_obj.drawCentredString(
            ancho / 2, 0.5 * inch,
            f"Documento generado automáticamente por Be Time el {fecha_texto}. "
            f"Código de verificación: {constancia.codigo}")
        canvas_obj.restoreState()

    estilos = getSampleStyleSheet()
    titulo = ParagraphStyle("t", parent=estilos["Title"], fontName="Helvetica-Bold", fontSize=17,
                            textColor=colors.HexColor(COLOR_VERDE), spaceAfter=18)
    cuerpo = ParagraphStyle("c", parent=estilos["BodyText"], fontName="Helvetica", fontSize=11,
                            leading=17, alignment=TA_JUSTIFY, spaceAfter=10)
    celda = ParagraphStyle("ce", fontName="Helvetica", fontSize=9, leading=11)
    celda_c = ParagraphStyle("cc", parent=celda, alignment=TA_CENTER)
    celda_h = ParagraphStyle("ch", parent=celda_c, fontName="Helvetica-Bold", textColor=colors.white)
    pequeno = ParagraphStyle("p", fontName="Helvetica", fontSize=8.5, leading=11,
                             textColor=colors.HexColor(COLOR_GRIS))

    e = escape  # los datos del aprendiz y los eventos nunca se interpretan como marcado
    elementos = [
        Spacer(1, 6),
        Paragraph("CONSTANCIA DE HORAS DE BIENESTAR", titulo),
        Paragraph(
            f"Be Time, plataforma de Bienestar al Aprendiz, hace constar que "
            f"<b>{e(constancia.nombre)}</b>, identificado(a) con "
            f"{e(constancia.tipo_documento)} No. <b>{e(constancia.numero_documento)}</b>, "
            f"aprendiz del programa de formación <b>{e(constancia.programa)}</b>, "
            f"grupo <b>{e(constancia.grupo)}</b>, tiene registradas "
            f"<b>{constancia.total_horas} horas</b> de bienestar, de las "
            f"{constancia.meta_horas} horas requeridas, según los registros de asistencia "
            f"a las actividades de Bienestar al Aprendiz a la fecha de expedición.",
            cuerpo),
    ]
    if constancia.total_horas >= constancia.meta_horas:
        elementos.append(Paragraph("El aprendiz <b>cumplió la meta</b> de horas de bienestar.", cuerpo))

    # ---------- Detalle por evento ----------
    registros = list(
        horas_de(aprendiz)
        .select_related("asistencia__inscripcion__evento")
        .order_by("asistencia__inscripcion__evento__fecha_inicio")
    )
    # Solo lo que se certificó ese día: horas registradas hasta la emisión.
    registros = [r for r in registros if r.fecha <= constancia.fecha_emision]
    filas = [[Paragraph("Actividad", celda_h), Paragraph("Fecha", celda_h), Paragraph("Horas", celda_h)]]
    for r in registros:
        evento = r.asistencia.inscripcion.evento
        filas.append([
            Paragraph(e(evento.titulo), celda),
            Paragraph(timezone.localtime(evento.fecha_inicio).strftime("%d/%m/%Y"), celda_c),
            Paragraph(str(r.cantidad_horas), celda_c),
        ])
    filas.append([Paragraph("<b>Total</b>", celda), "", Paragraph(f"<b>{constancia.total_horas}</b>", celda_c)])

    tabla = Table(filas, colWidths=[4.2 * inch, 1.5 * inch, 0.9 * inch], repeatRows=1)
    tabla.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor(COLOR_VERDE)),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor(COLOR_BORDE)),
        ("ROWBACKGROUNDS", (0, 1), (-1, -2), [colors.white, colors.HexColor("#F3F8F0")]),
        ("BACKGROUND", (0, -1), (-1, -1), colors.HexColor("#E9F2E4")),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]))
    elementos += [tabla, Spacer(1, 18)]

    # ---------- Verificación ----------
    qr = Image(_qr_imagen(url_verificacion), width=1.15 * inch, height=1.15 * inch)
    texto_verif = Paragraph(
        f"<b>Verifica la autenticidad</b><br/>Escanea el código QR o ingresa a:<br/>"
        f"{e(url_verificacion)}<br/><br/>Código: <b>{constancia.codigo}</b><br/>"
        f"Expedida el {fecha_texto}.", pequeno)
    bloque = Table([[qr, texto_verif]], colWidths=[1.35 * inch, 5.0 * inch])
    bloque.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                                ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor(COLOR_BORDE)),
                                ("LEFTPADDING", (0, 0), (-1, -1), 8)]))
    elementos.append(KeepTogether([bloque]))

    buffer = BytesIO()
    SimpleDocTemplate(
        buffer, pagesize=letter, topMargin=1.4 * inch, bottomMargin=0.9 * inch,
        leftMargin=0.8 * inch, rightMargin=0.8 * inch,
        title=f"Constancia de horas de bienestar - {constancia.nombre}",
    ).build(elementos, onFirstPage=membrete, onLaterPages=membrete)
    return buffer.getvalue()
