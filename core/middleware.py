class NoCacheParaAutenticadosMiddleware:
    """
    Evita que el navegador guarde en caché local las páginas vistas
    mientras el usuario tenía sesión activa.

    Sin esto: cerrar sesión y luego usar el botón "atrás" del
    navegador puede mostrar una copia vieja guardada localmente de
    una pantalla del panel (dashboard, aprendices, eventos...), en
    vez de pedírsela de nuevo al servidor. La sesión en el servidor
    sí queda cerrada correctamente (logout() ya la invalida) -- lo
    que pasa es que el navegador nunca vuelve a preguntar, porque
    tenía la página guardada localmente.

    Con este middleware, cualquier respuesta servida mientras
    request.user está autenticado lleva encabezados que le prohíben
    al navegador guardarla: al darle "atrás", se ve forzado a
    pedírsela de nuevo al servidor, que en ese momento sí detecta
    que la sesión ya no existe y redirige al login.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)

        if request.user.is_authenticated:
            response["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
            response["Pragma"] = "no-cache"

        return response
