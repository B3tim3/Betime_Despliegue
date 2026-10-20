# Administrador crea usuarios (entrega 16)

8 archivos. Sin migraciones, sin dependencias nuevas.

## 1. Copia los 8 archivos a su ruta exacta

`usuarios/forms/crear_usuario.py` y `templates/usuarios/crear_usuario.html` son nuevos.

## 2. Qué se implementó

Nueva sección en el panel, **solo visible para Administrador** (enlace
"Crear usuario" en el sidebar), donde puede crear:

- **Aprendices** — pide programa y ficha (con el mismo desplegable en
  cascada que ya usa el registro público).
- **Personal de Bienestar** — pide el cargo (texto libre, es solo
  informativo, no cambia permisos).
- **Otros Administradores** — solo los datos básicos.

El campo "Tipo de cuenta a crear" es lo primero del formulario, y
según lo que elijas, aparecen o desaparecen los campos que solo
aplican a ese tipo (JavaScript simple, sin recargar la página).

## 3. Diseño, para que quede claro

- Reutiliza el mismo patrón de `registrar_aprendiz` — un service
  (`crear_usuario_administrativo`) que crea el `Usuario` y su perfil
  de forma atómica (si algo falla a mitad de camino, no queda un
  usuario sin perfil).
- **Diferencia clave con el registro público:** ahí la persona se
  registra a sí misma y queda con sesión iniciada de una vez. Aquí es
  el Administrador quien crea la cuenta de alguien más, así que no
  hace login automático — solo confirma que se creó, y la persona
  inicia sesión después con sus propias credenciales.
- Las mismas validaciones de siempre: documento no repetido, correo
  no repetido, política de contraseñas de Django, confirmación de
  contraseña.

## 4. Prueba

1. Entra como Laura (Administrador) → sidebar → "Crear usuario".
2. Crea un Aprendiz nuevo — confirma que el desplegable de fichas
   cambia según el programa que elijas.
3. Cambia el tipo a "Personal de Bienestar" — deben desaparecer los
   campos de programa/ficha y aparecer el de cargo.
4. Cambia a "Administrador" — no debe pedir nada extra, solo los
   datos básicos.
5. Crea uno de cada tipo, cierra sesión, e inicia sesión con esa
   cuenta nueva para confirmar que cae en el panel correcto.
6. Intenta crear un usuario con un documento que ya exista (por
   ejemplo, 1000000001) — debe rechazarlo con el mismo mensaje de
   siempre.
