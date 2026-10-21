"""
Prueba que las migraciones 0005-0008 (Ficha -> Grupo y nivel de formación
como catálogo) conservan los datos que ya existían.

Se ejecuta con:   python manage.py test usuarios.test_migraciones
"""

from datetime import date

from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.test import TransactionTestCase


class MigracionGruposYNivelesTests(TransactionTestCase):

    migrar_desde = [("usuarios", "0004_genero_telefono_usuario")]
    migrar_hasta = [("usuarios", "0008_nivel_formacion_obligatorio")]

    def migrar(self, destino):
        ejecutor = MigrationExecutor(connection)
        ejecutor.migrate(destino)
        return ejecutor.loader.project_state(destino).apps

    def setUp(self):
        # 1) Base en el estado ANTERIOR (modelo Ficha, nivel como texto) con datos.
        antes = self.migrar(self.migrar_desde)

        Jornada = antes.get_model("usuarios", "Jornada")
        Programa = antes.get_model("usuarios", "ProgramaFormacion")
        Ficha = antes.get_model("usuarios", "Ficha")
        Usuario = antes.get_model("usuarios", "Usuario")
        Aprendiz = antes.get_model("usuarios", "Aprendiz")

        jornada = Jornada.objects.create(nombre="Diurna")
        # Mismo nivel escrito de tres formas + uno vacío + uno distinto
        p1 = Programa.objects.create(nombre="ADSO", codigo="1", nivel_formacion="Tecnólogo", duracion_meses=24)
        p2 = Programa.objects.create(nombre="Multimedia", codigo="2", nivel_formacion=" tecnologo ", duracion_meses=24)
        p3 = Programa.objects.create(nombre="Sistemas", codigo="3", nivel_formacion="TÉCNICO", duracion_meses=12)
        p4 = Programa.objects.create(nombre="Otro", codigo="4", nivel_formacion="", duracion_meses=6)
        p5 = Programa.objects.create(nombre="Esp", codigo="5", nivel_formacion="Especialización", duracion_meses=12)
        self.ids = (p1.id, p2.id, p3.id, p4.id, p5.id)

        ficha = Ficha.objects.create(
            numero_ficha="3171693", programa_formacion=p1, jornada=jornada,
            fecha_inicio=date(2026, 1, 1), fecha_fin=date(2027, 1, 1),
        )
        usuario = Usuario.objects.create(
            numero_documento="100", tipo_documento="CC", nombres="Ana", apellidos="Gómez",
            email="ana@example.com", password="x",
        )
        Aprendiz.objects.create(usuario=usuario, ficha=ficha, fecha_ingreso=date(2026, 1, 2))

    def tearDown(self):
        # Deja la base de pruebas en el último estado para el resto de tests.
        MigrationExecutor(connection).migrate(
            MigrationExecutor(connection).loader.graph.leaf_nodes()
        )

    def test_los_datos_sobreviven(self):
        despues = self.migrar(self.migrar_hasta)

        Grupo = despues.get_model("usuarios", "Grupo")
        Aprendiz = despues.get_model("usuarios", "Aprendiz")
        Programa = despues.get_model("usuarios", "ProgramaFormacion")
        Nivel = despues.get_model("usuarios", "NivelFormacion")

        # Ficha -> Grupo: el registro y su vínculo con el aprendiz siguen ahí.
        grupo = Grupo.objects.get()
        self.assertEqual(grupo.numero_grupo, "3171693")
        self.assertEqual(Aprendiz.objects.get().grupo_id, grupo.id)

        # Niveles: variantes unificadas, nada duplicado.
        nombres = set(Nivel.objects.values_list("nombre", flat=True))
        self.assertEqual(nombres, {"Técnico", "Tecnólogo", "Sin definir", "Especialización"})

        niveles = {p.nombre: p.nivel_formacion.nombre for p in Programa.objects.select_related("nivel_formacion")}
        self.assertEqual(niveles, {
            "ADSO": "Tecnólogo", "Multimedia": "Tecnólogo", "Sistemas": "Técnico",
            "Otro": "Sin definir", "Esp": "Especialización",
        })
