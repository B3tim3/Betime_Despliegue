"""Cupo máximo de asistentes en actividades."""

import threading
from datetime import date, timedelta

from django.db import connection
from django.test import TestCase, TransactionTestCase
from django.urls import reverse
from django.utils import timezone

from actividades.forms import ActividadForm
from actividades.models import Actividad, Inscripcion
from actividades.services.inscripciones import CupoAgotadoError, InscripcionError, cancelar, inscribir
from usuarios.models import (
    Aprendiz, Grupo, Jornada, NivelFormacion, PersonalBienestar, ProgramaFormacion, Usuario,
)

CLAVE = "x"


def crear_datos():
    nivel, _ = NivelFormacion.objects.get_or_create(nombre="Tecnólogo")
    jor = Jornada.objects.create(nombre="Diurna")
    prog = ProgramaFormacion.objects.create(nombre="ADSO", codigo="P1", nivel_formacion=nivel, duracion_meses=24)
    grupo = Grupo.objects.create(numero_grupo="3000001", programa_formacion=prog, jornada=jor,
                                 fecha_inicio=date(2026, 1, 1), fecha_fin=date(2027, 1, 1))
    staff = Usuario.objects.create_user(numero_documento="900", password=CLAVE, tipo_documento="CC",
                                        nombres="Paola", apellidos="R", email="p@x.co")
    PersonalBienestar.objects.create(usuario=staff, cargo="C", fecha_ingreso=date(2026, 1, 1))
    aprendices = []
    for i in range(1, 6):
        u = Usuario.objects.create_user(numero_documento=f"10{i}", password=CLAVE, tipo_documento="CC",
                                        nombres=f"Ana{i}", apellidos="P", email=f"a{i}@x.co")
        aprendices.append(Aprendiz.objects.create(usuario=u, grupo=grupo, fecha_ingreso=date(2026, 1, 1)))
    return staff, aprendices


def crear_actividad(staff, cupo=None, titulo="Yoga"):
    ini = timezone.now() + timedelta(days=3)
    return Actividad.objects.create(titulo=titulo, lugar="L", horas_otorgadas=1, creado_por=staff,
                                 fecha_inicio=ini, fecha_fin=ini + timedelta(hours=2), cupo_maximo=cupo)


class CupoTests(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.staff, cls.aps = crear_datos()

    def test_sin_cupo_no_hay_limite(self):
        e = crear_actividad(self.staff)
        for a in self.aps:
            inscribir(a, e)
        self.assertIsNone(e.cupos_disponibles)
        self.assertFalse(e.esta_lleno)
        self.assertEqual(e.inscritos_activos, 5)

    def test_se_llena_y_rechaza_con_mensaje_claro(self):
        e = crear_actividad(self.staff, cupo=2)
        inscribir(self.aps[0], e)
        inscribir(self.aps[1], e)
        with self.assertRaises(CupoAgotadoError) as cm:
            inscribir(self.aps[2], e)
        self.assertIn("agotaron", str(cm.exception))
        self.assertIsInstance(cm.exception, InscripcionError)
        self.assertFalse(Inscripcion.objects.filter(actividad=e, aprendiz=self.aps[2]).exists())
        self.assertTrue(e.esta_lleno)
        self.assertEqual(e.cupos_disponibles, 0)

    def test_quien_ya_estaba_inscrito_no_choca_con_el_cupo(self):
        e = crear_actividad(self.staff, cupo=1)
        inscribir(self.aps[0], e)
        _, accion = inscribir(self.aps[0], e)       # lleno, pero ya tiene su lugar
        self.assertEqual(accion, "existente")

    def test_cancelar_libera_el_lugar(self):
        e = crear_actividad(self.staff, cupo=1)
        insc, _ = inscribir(self.aps[0], e)
        with self.assertRaises(CupoAgotadoError):
            inscribir(self.aps[1], e)
        cancelar(insc)
        self.assertEqual(Actividad.objects.get(pk=e.pk).cupos_disponibles, 1)
        inscribir(self.aps[1], e)                   # ahora sí cabe

    def test_reinscribirse_tras_cancelar_tambien_respeta_el_cupo(self):
        e = crear_actividad(self.staff, cupo=1)
        insc, _ = inscribir(self.aps[0], e)
        cancelar(insc)
        inscribir(self.aps[1], e)                   # otra persona toma el lugar
        with self.assertRaises(CupoAgotadoError):
            inscribir(self.aps[0], e)               # la primera ya no cabe
        self.assertEqual(Inscripcion.objects.get(actividad=e, aprendiz=self.aps[0]).estado, "cancelada")

    def test_las_canceladas_no_ocupan_lugar_pero_las_que_asistieron_si(self):
        e = crear_actividad(self.staff, cupo=3)
        i1, _ = inscribir(self.aps[0], e)
        i2, _ = inscribir(self.aps[1], e)
        inscribir(self.aps[2], e)
        cancelar(i1)
        Inscripcion.objects.filter(pk=i2.pk).update(estado="asistio")
        self.assertEqual(e.inscritos_activos, 2)

    def test_con_cupos_cuenta_en_la_misma_consulta(self):
        e = crear_actividad(self.staff, cupo=5)
        inscribir(self.aps[0], e)
        inscribir(self.aps[1], e)
        otro = crear_actividad(self.staff, titulo="Otro")
        with self.assertNumQueries(1):
            datos = {x.pk: x.inscritos_activos for x in Actividad.objects.con_cupos()}
        self.assertEqual(datos, {e.pk: 2, otro.pk: 0})

    def test_valor_invalido_en_la_base(self):
        from django.db import IntegrityError, transaction
        e = crear_actividad(self.staff)
        with self.assertRaises(IntegrityError), transaction.atomic():
            Actividad.objects.filter(pk=e.pk).update(cupo_maximo=0)


class CupoFormularioTests(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.staff, cls.aps = crear_datos()

    def datos(self, cupo):
        ini = timezone.now() + timedelta(days=3)
        return {"titulo": "E", "lugar": "L", "horas_otorgadas": 1, "estado": "", "cupo_maximo": cupo,
                "fecha_inicio": ini.strftime("%Y-%m-%d %H:%M"),
                "fecha_fin": (ini + timedelta(hours=2)).strftime("%Y-%m-%d %H:%M")}

    def test_vacio_es_sin_limite(self):
        form = ActividadForm(self.datos(""))
        self.assertTrue(form.is_valid(), form.errors)
        self.assertIsNone(form.cleaned_data["cupo_maximo"])

    def test_cero_o_negativo_no_se_aceptan(self):
        for malo in ("0", "-3"):
            self.assertFalse(ActividadForm(self.datos(malo)).is_valid())

    def test_no_se_puede_bajar_el_cupo_por_debajo_de_los_inscritos(self):
        e = crear_actividad(self.staff, cupo=5)
        for a in self.aps[:3]:
            inscribir(a, e)
        form = ActividadForm(self.datos("2"), instance=e)
        self.assertFalse(form.is_valid())
        self.assertIn("Ya hay 3 aprendices inscritos", form.errors["cupo_maximo"][0])
        self.assertTrue(ActividadForm(self.datos("3"), instance=e).is_valid())
        self.assertTrue(ActividadForm(self.datos(""), instance=e).is_valid())

    def test_las_canceladas_no_cuentan_al_bajar_el_cupo(self):
        e = crear_actividad(self.staff, cupo=5)
        i1, _ = inscribir(self.aps[0], e)
        inscribir(self.aps[1], e)
        cancelar(i1)
        self.assertTrue(ActividadForm(self.datos("1"), instance=e).is_valid())


class CupoPantallasTests(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.staff, cls.aps = crear_datos()

    def entrar(self, doc):
        self.client.login(numero_documento=doc, password=CLAVE)

    def test_detalle_muestra_cupos_y_boton_cuando_hay_lugar(self):
        e = crear_actividad(self.staff, cupo=3)
        inscribir(self.aps[0], e)
        self.entrar("102")
        r = self.client.get(reverse("actividades:detalle", args=[e.id]))
        self.assertContains(r, "2 disponibles de 3")
        self.assertContains(r, "Inscribirme")

    def test_detalle_lleno_oculta_el_boton(self):
        e = crear_actividad(self.staff, cupo=1)
        inscribir(self.aps[0], e)
        self.entrar("102")
        r = self.client.get(reverse("actividades:detalle", args=[e.id]))
        self.assertContains(r, "Cupos agotados")
        self.assertNotContains(r, "Inscribirme")

    def test_detalle_lleno_para_visitante_sin_sesion(self):
        e = crear_actividad(self.staff, cupo=1)
        inscribir(self.aps[0], e)
        r = self.client.get(reverse("actividades:detalle", args=[e.id]))
        self.assertContains(r, "Cupos agotados")
        self.assertNotContains(r, "Inicia sesión para inscribirte")

    def test_el_inscrito_sigue_viendo_su_qr_aunque_este_lleno(self):
        e = crear_actividad(self.staff, cupo=1)
        inscribir(self.aps[0], e)
        self.entrar("101")
        r = self.client.get(reverse("actividades:detalle", args=[e.id]))
        self.assertContains(r, "Ya estás inscrito")
        self.assertContains(r, "Ver mi código QR")

    def test_post_directo_a_un_actividad_lleno_es_rechazado(self):
        e = crear_actividad(self.staff, cupo=1)
        inscribir(self.aps[0], e)
        self.entrar("102")
        r = self.client.post(reverse("actividades:inscribirse", args=[e.id]), follow=True)
        self.assertContains(r, "agotaron")
        self.assertEqual(e.inscripciones.count(), 1)

    def test_lista_publica_y_paneles(self):
        e = crear_actividad(self.staff, cupo=1, titulo="Con cupo")
        inscribir(self.aps[0], e)
        crear_actividad(self.staff, titulo="Libre")
        self.assertContains(self.client.get(reverse("actividades:lista")), "Cupos agotados")
        self.entrar("900")
        r = self.client.get(reverse("actividades:panel_lista"))
        self.assertContains(r, "1 / 1")
        self.assertContains(r, "Lleno")
        self.assertContains(r, "sin límite")
        r = self.client.get(reverse("actividades:panel_inscritos", args=[e.id]))
        self.assertContains(r, "Cupo: 1 / 1")

    def test_crear_actividad_con_cupo_desde_el_formulario(self):
        self.entrar("900")
        r = self.client.get(reverse("actividades:crear"))
        self.assertContains(r, 'name="cupo_maximo"')


class CupoConcurrenciaTests(TransactionTestCase):
    """Dos aprendices pulsan «Inscribirme» a la vez por el ÚLTIMO lugar: solo entra uno."""

    def test_carrera_por_el_ultimo_cupo(self):
        staff, aps = crear_datos()
        e = crear_actividad(staff, cupo=1)
        resultados, barrera = [], threading.Barrier(4)

        def intentar(ap):
            try:
                barrera.wait()
                inscribir(ap, e)
                resultados.append("ok")
            except CupoAgotadoError:
                resultados.append("lleno")
            finally:
                connection.close()

        hilos = [threading.Thread(target=intentar, args=(a,)) for a in aps[:4]]
        [h.start() for h in hilos]
        [h.join() for h in hilos]
        self.assertEqual(sorted(resultados), ["lleno", "lleno", "lleno", "ok"])
        self.assertEqual(Inscripcion.objects.filter(actividad=e).count(), 1)
