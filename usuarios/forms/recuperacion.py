import os
from email.message import EmailMessage as MensajeMIME
from email.utils import formatdate, make_msgid
from urllib.parse import urlparse

from django.conf import settings
from django.contrib.auth.forms import PasswordResetForm, SetPasswordForm
from django.contrib.staticfiles import finders
from django.core.mail import EmailMultiAlternatives
from django.template import loader


class _CorreoConLogo(EmailMultiAlternatives):
    """
    Correo texto + HTML con el logo EMBEBIDO. La estructura MIME correcta es
    multipart/alternative( texto , multipart/related( html , logo ) ): así el
    logo se ve en Gmail, Outlook y Apple Mail sin depender de que el cliente
    descargue imágenes remotas (que además no existirían con el sitio en localhost).
    Django 6 ya no deja armar el "related" a mano, por eso se construye aquí.
    """

    def __init__(self, *args, texto, html, logo_png=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.attach_alternative(html, "text/html")   # para que se pueda inspeccionar (y en pruebas)
        self._texto, self._html, self._logo = texto, html, logo_png

    def message(self, *args, **kwargs):
        msg = MensajeMIME()
        msg["Subject"] = self.subject
        msg["From"] = self.from_email
        msg["To"] = ", ".join(self.to)
        msg["Date"] = formatdate(localtime=True)
        msg["Message-ID"] = make_msgid()
        msg.set_content(self._texto)
        msg.add_alternative(self._html, subtype="html")
        if self._logo:
            msg.get_payload()[1].add_related(self._logo, "image", "png", cid="<logo-betime>", filename="logo.png")
        return msg


def _texto_duracion(segundos):
    """1200 -> '20 minutos'; 3600 -> '1 hora'; 259200 -> '3 días'."""
    for unidad, singular, plural in ((86400, "día", "días"), (3600, "hora", "horas"), (60, "minuto", "minutos")):
        if segundos >= unidad and segundos % unidad == 0:
            n = segundos // unidad
            return f"{n} {singular if n == 1 else plural}"
    return f"{max(segundos // 60, 1)} minutos"


def _documento_oculto(documento):
    """Muestra solo los últimos 3 dígitos: el correo confirma la cuenta sin exponer el documento."""
    documento = str(documento or "")
    return "•" * max(len(documento) - 3, 0) + documento[-3:]


class RecuperarContrasenaForm(PasswordResetForm):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["email"].widget.attrs.update({
            "class": "form-control",
            "autocomplete": "email",
        })

    def save(self, domain_override=None, use_https=False, request=None, **kwargs):
        """
        Decide a qué dirección apunta el enlace del correo.

        1) Si existe la variable SITE_URL (en .env o en el servidor), se usa ESA: es la
           dirección pública real del sitio. Hace falta con un túnel (cloudflared/ngrok),
           porque el túnel entrega la petición con "Host: localhost" y Django no tiene
           forma de saber la dirección pública; sin esto el enlace salía con localhost.
        2) Si no, se usa la de la petición (correcto en producción: Render, dominio propio),
           y se respeta X-Forwarded-Proto para que sea https detrás de un proxy.

        A propósito NO se toma la dirección de cabeceras que envía el visitante (Origin,
        Referer...): un atacante podría pedir el correo de OTRA persona con una cabecera
        falsa y hacer que su enlace de recuperación apunte a un sitio malicioso.
        """
        base = os.environ.get("SITE_URL", "").strip().rstrip("/")
        if base:
            if "://" not in base:
                base = "https://" + base
            partes = urlparse(base)
            domain_override, use_https = partes.netloc, partes.scheme == "https"
        elif request is not None and request.META.get("HTTP_X_FORWARDED_PROTO", "").split(",")[0].strip() == "https":
            use_https = True
        return super().save(domain_override=domain_override, use_https=use_https, request=request, **kwargs)

    def send_mail(self, subject_template_name, email_template_name, context, from_email,
                  to_email, html_email_template_name=None):
        """
        Igual que el de Django, pero el correo HTML lleva el logo EMBEBIDO (adjunto
        inline con Content-ID), no como enlace: así se ve aunque el sitio esté en
        localhost o el cliente de correo bloquee imágenes remotas. Además de la
        versión HTML siempre va la de texto plano, por si el cliente no muestra HTML.
        """
        usuario = context["user"]
        segundos = settings.PASSWORD_RESET_TIMEOUT
        context = {
            **context,
            "nombre": usuario.get_full_name() or "aprendiz",
            "documento_oculto": _documento_oculto(usuario.numero_documento),
            "vigencia": _texto_duracion(segundos),
        }

        asunto = "".join(loader.render_to_string(subject_template_name, context).splitlines())
        texto = loader.render_to_string(email_template_name, context)
        html = loader.render_to_string(html_email_template_name, context) if html_email_template_name else None

        logo = None
        ruta_logo = finders.find("img/logo.png")
        if ruta_logo:
            with open(ruta_logo, "rb") as archivo:
                logo = archivo.read()

        if html is None:
            EmailMultiAlternatives(asunto, texto, from_email, [to_email]).send()
            return
        mensaje = _CorreoConLogo(asunto, texto, from_email, [to_email], texto=texto, html=html, logo_png=logo)
        mensaje.send()


class NuevaContrasenaForm(SetPasswordForm):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["new_password1"].widget.attrs.update({
            "class": "form-control",
            "autocomplete": "new-password",
        })
        self.fields["new_password2"].widget.attrs.update({
            "class": "form-control",
            "autocomplete": "new-password",
        })
