"""
Inicio y cierre de sesión, registro de aprendices y las consultas AJAX del formulario de registro.
"""

from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.db.models import F
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.views.decorators.http import require_POST

from usuarios.forms import LoginForm, RegistroAprendizForm
from usuarios.models import Grupo, Jornada, ProgramaFormacion
from usuarios.services import registrar_aprendiz
from usuarios.services.bloqueo import (
    ip_del_cliente,
    limpiar,
    minutos_de_bloqueo,
    registrar_fallo,
)


def jornadas_por_programa(request):
    """
    Devuelve en JSON las jornadas en las que el programa elegido tiene
    grupos activos, junto con el nivel de formación del programa.
    Es el segundo escalón de la cascada del registro:
    programa -> jornada -> grupo.
    """

    programa_id = request.GET.get("programa_formacion")

    if not programa_id or not programa_id.isdigit():
        return JsonResponse({"nivel": "", "jornadas": []})

    programa = ProgramaFormacion.objects.select_related("nivel_formacion").filter(
        pk=programa_id, estado="activo"
    ).first()

    if programa is None:
        return JsonResponse({"nivel": "", "jornadas": []})

    jornadas = Jornada.objects.filter(
        grupos__programa_formacion=programa,
        grupos__estado="activa",
    ).distinct().order_by("nombre").values("id", "nombre")

    return JsonResponse({
        "nivel": programa.nivel_formacion.nombre,
        "jornadas": list(jornadas),
    })


def grupos_por_programa(request):
    """
    Devuelve en JSON los grupos activos de un programa de
    formación. Si además llega ?jornada=<id>, solo los de esa jornada.
    Es el último escalón de la cascada del registro. El parámetro
    jornada es opcional para no romper el formulario de creación de
    usuarios del panel, que solo filtra por programa.
    """

    programa_id = request.GET.get("programa_formacion")
    jornada_id = request.GET.get("jornada")

    if not programa_id or not programa_id.isdigit():
        return JsonResponse([], safe=False)

    grupos = Grupo.objects.filter(
        programa_formacion_id=programa_id,
        estado="activa"
    )

    if jornada_id and jornada_id.isdigit():
        grupos = grupos.filter(jornada_id=jornada_id)

    grupos = grupos.order_by("numero_grupo").values(
        "id", "numero_grupo", jornada_nombre=F("jornada__nombre")
    )

    return JsonResponse(list(grupos), safe=False)


def registro_aprendiz(request):

    if request.user.is_authenticated:
        return redirect("usuarios:dashboard")

    form = RegistroAprendizForm(request.POST or None)

    if request.method == "POST" and form.is_valid():

        usuario, aprendiz = registrar_aprendiz(
            tipo_documento=form.cleaned_data["tipo_documento"],
            numero_documento=form.cleaned_data["numero_documento"],
            nombres=form.cleaned_data["nombres"],
            apellidos=form.cleaned_data["apellidos"],
            email=form.cleaned_data["email"],
            password=form.cleaned_data["password"],
            grupo=form.cleaned_data["grupo"],
            genero=form.cleaned_data["genero"],
            telefono=form.cleaned_data["telefono"],
        )

        login(request, usuario)
        messages.success(request, "¡Tu cuenta se creó correctamente! Bienvenido a Be Time.")
        return redirect("usuarios:dashboard")

    return render(request, "usuarios/registro.html", {"form": form})


def login_view(request):

    if request.user.is_authenticated:
        return redirect("usuarios:dashboard")

    form = LoginForm(request.POST or None)

    if request.method == "POST":

        # Se mira el bloqueo ANTES de probar nada, con el documento tal como
        # llegó (aunque el formulario no sea válido, para que un documento
        # bloqueado no sirva ni para ver otros mensajes de error).
        documento_enviado = request.POST.get("numero_documento", "")
        espera = minutos_de_bloqueo(documento_enviado)

        if espera:
            messages.error(
                request,
                f"Demasiados intentos fallidos. Por seguridad, espera {espera} "
                f"minuto{'s' if espera != 1 else ''} antes de volver a intentarlo."
            )
        elif form.is_valid():
            numero_documento = form.cleaned_data["numero_documento"]
            password = form.cleaned_data["password"]

            usuario = authenticate(
                request,
                username=numero_documento,
                password=password
            )

            if usuario is not None:
                limpiar(numero_documento)
                login(request, usuario)
                return redirect("usuarios:dashboard")

            registrar_fallo(numero_documento, ip_del_cliente(request))
            messages.error(request, "Documento o contraseña incorrectos.")
        else:
            # Formulario inválido (por ejemplo, tipo de documento que no
            # coincide): también cuenta como intento fallido.
            registrar_fallo(documento_enviado, ip_del_cliente(request))

    # "acceso-personal/" es la misma vista y el mismo formulario que
    # "login/" -- lo único que cambia es que ahí no tiene sentido
    # mostrar los enlaces de "olvidé mi contraseña" / "crea tu cuenta
    # de aprendiz", pensados para aprendices, no para Bienestar/Admin.
    es_acceso_personal = request.resolver_match.url_name == "login_personal"

    return render(request, "usuarios/login.html", {
        "form": form,
        "es_acceso_personal": es_acceso_personal,
    })


@require_POST
def logout_view(request):
    # Solo POST: con un enlace GET, cualquier página o imagen externa podría
    # cerrarle la sesión a la persona sin que lo note.
    logout(request)
    messages.success(request, "Sesión cerrada correctamente.")
    return redirect("index")
