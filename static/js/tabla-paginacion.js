/*
 * Paginación client-side para tablas del panel.
 *
 * Funciona junto con tabla-filtro.js: cuando el buscador oculta filas,
 * la paginación se recalcula solo con las filas visibles.
 *
 * Uso:
 *   <table id="mi-tabla" data-tabla-paginada>
 *
 * Genera automáticamente:
 *   - Selector "Mostrar X registros" (10, 25, 50, 100)
 *   - Paginación numérica con elipsis (1 ... 4 5 6 ... 20)
 *   - Contador "Mostrando 1-10 de 85 registros"
 *
 * Se integra con el buscador (data-tabla-filtro) y el filtro de estado
 * (data-tabla-filtro-estado): cada vez que cambian, recalcula.
 */
document.addEventListener("DOMContentLoaded", function () {

    document.querySelectorAll("table[data-tabla-paginada]").forEach(function (tabla) {

        var tablaId = tabla.id;
        if (!tablaId) return;

        var tbody = tabla.querySelector("tbody");
        if (!tbody) return;

        var todasLasFilas = Array.from(tbody.querySelectorAll("tr"));
        if (todasLasFilas.length === 0) return;

        // ---------- Estado ----------
        var porPagina = 10;
        var paginaActual = 1;

        // ---------- Construir controles ----------

        // Contenedor superior: selector de registros
        var controlesSuperior = document.createElement("div");
        controlesSuperior.className = "tabla-pag-superior";
        controlesSuperior.innerHTML =
            '<div class="tabla-pag-registros">' +
                '<span>Mostrar</span>' +
                '<select class="tabla-pag-select">' +
                    '<option value="10">10</option>' +
                    '<option value="25">25</option>' +
                    '<option value="50">50</option>' +
                    '<option value="100">100</option>' +
                '</select>' +
                '<span>registros</span>' +
            '</div>';

        // Contenedor inferior: contador + paginación
        var controlesInferior = document.createElement("div");
        controlesInferior.className = "tabla-pag-inferior";
        controlesInferior.innerHTML =
            '<div class="tabla-pag-info"></div>' +
            '<nav class="tabla-pag-nav" aria-label="Paginación"></nav>';

        // Insertar antes y después de la tabla (o su .table-responsive)
        var contenedorTabla = tabla.closest(".table-responsive") || tabla;
        contenedorTabla.parentNode.insertBefore(controlesSuperior, contenedorTabla);
        contenedorTabla.parentNode.insertBefore(controlesInferior, contenedorTabla.nextSibling);

        var selectRegistros = controlesSuperior.querySelector(".tabla-pag-select");
        var infoDiv = controlesInferior.querySelector(".tabla-pag-info");
        var navDiv = controlesInferior.querySelector(".tabla-pag-nav");

        // Ocultar la paginación vieja de Django si existe
        var paginacionVieja = contenedorTabla.parentNode.querySelector(".pagination");
        if (paginacionVieja) {
            var navVieja = paginacionVieja.closest("nav");
            if (navVieja) navVieja.style.display = "none";
        }

        // ---------- Lógica de paginación ----------

        function filasVisibles() {
            return todasLasFilas.filter(function (fila) {
                // Una fila puede estar oculta por el buscador/filtro
                // (display: none puesto por tabla-filtro.js)
                return fila.style.display !== "none" || fila.getAttribute("data-pag-oculta") === "1";
            });
        }

        function obtenerFilasFiltradas() {
            // Primero mostrar todas las filas para que el filtro funcione
            // Luego obtener las que el filtro deja visibles
            var resultado = [];
            todasLasFilas.forEach(function (fila) {
                // Si está oculta por paginación pero no por filtro, es visible para nosotros
                var ocultaPorPag = fila.getAttribute("data-pag-oculta") === "1";
                var ocultaPorFiltro = !ocultaPorPag && fila.style.display === "none";

                if (!ocultaPorFiltro) {
                    resultado.push(fila);
                }
            });
            return resultado;
        }

        function renderizar() {
            // Mostrar todas primero (quitar ocultamiento de paginación)
            todasLasFilas.forEach(function (fila) {
                if (fila.getAttribute("data-pag-oculta") === "1") {
                    fila.style.display = "";
                    fila.removeAttribute("data-pag-oculta");
                }
            });

            // Obtener filas que pasan el filtro
            var filtradas = [];
            todasLasFilas.forEach(function (fila) {
                if (fila.style.display !== "none") {
                    filtradas.push(fila);
                }
            });

            var total = filtradas.length;
            var totalPaginas = Math.max(1, Math.ceil(total / porPagina));

            if (paginaActual > totalPaginas) paginaActual = totalPaginas;

            var inicio = (paginaActual - 1) * porPagina;
            var fin = Math.min(inicio + porPagina, total);

            // Ocultar las que no van en esta página (marcándolas como ocultas por paginación)
            filtradas.forEach(function (fila, i) {
                if (i < inicio || i >= fin) {
                    fila.style.display = "none";
                    fila.setAttribute("data-pag-oculta", "1");
                }
            });

            // Info
            if (total === 0) {
                infoDiv.textContent = "Sin resultados";
            } else {
                infoDiv.textContent = "Mostrando " + (inicio + 1) + "–" + fin + " de " + total + " registros";
            }

            // Paginación numérica
            renderizarPaginacion(totalPaginas);
        }

        function renderizarPaginacion(totalPaginas) {
            if (totalPaginas <= 1) {
                navDiv.innerHTML = "";
                return;
            }

            var paginas = generarRangoPaginas(paginaActual, totalPaginas);
            var html = '<ul class="tabla-pag-lista">';

            // Botón anterior
            html += '<li class="tabla-pag-item' + (paginaActual === 1 ? ' disabled' : '') + '">';
            html += '<button class="tabla-pag-btn" data-pagina="' + (paginaActual - 1) + '"' + (paginaActual === 1 ? ' disabled' : '') + '>';
            html += '<i class="bi bi-chevron-left"></i></button></li>';

            paginas.forEach(function (p) {
                if (p === "...") {
                    html += '<li class="tabla-pag-item tabla-pag-ellipsis"><span>…</span></li>';
                } else {
                    html += '<li class="tabla-pag-item' + (p === paginaActual ? ' active' : '') + '">';
                    html += '<button class="tabla-pag-btn" data-pagina="' + p + '">' + p + '</button></li>';
                }
            });

            // Botón siguiente
            html += '<li class="tabla-pag-item' + (paginaActual === totalPaginas ? ' disabled' : '') + '">';
            html += '<button class="tabla-pag-btn" data-pagina="' + (paginaActual + 1) + '"' + (paginaActual === totalPaginas ? ' disabled' : '') + '>';
            html += '<i class="bi bi-chevron-right"></i></button></li>';

            html += '</ul>';
            navDiv.innerHTML = html;

            // Eventos de clic
            navDiv.querySelectorAll("button[data-pagina]").forEach(function (btn) {
                btn.addEventListener("click", function () {
                    var p = parseInt(btn.getAttribute("data-pagina"), 10);
                    if (p >= 1 && p <= totalPaginas) {
                        paginaActual = p;
                        renderizar();
                        // Scroll suave al inicio de la tabla
                        contenedorTabla.scrollIntoView({ behavior: "smooth", block: "start" });
                    }
                });
            });
        }

        function generarRangoPaginas(actual, total) {
            // Siempre muestra: primera, última, actual, y ±1 de actual
            // Con elipsis donde haga falta
            if (total <= 7) {
                var arr = [];
                for (var i = 1; i <= total; i++) arr.push(i);
                return arr;
            }

            var paginas = [];
            var izquierda = Math.max(2, actual - 1);
            var derecha = Math.min(total - 1, actual + 1);

            // Ajustar para siempre mostrar al menos 3 números centrales
            if (actual <= 3) {
                derecha = Math.min(total - 1, 4);
            }
            if (actual >= total - 2) {
                izquierda = Math.max(2, total - 3);
            }

            paginas.push(1);

            if (izquierda > 2) paginas.push("...");

            for (var j = izquierda; j <= derecha; j++) {
                paginas.push(j);
            }

            if (derecha < total - 1) paginas.push("...");

            paginas.push(total);

            return paginas;
        }

        // ---------- Eventos ----------

        selectRegistros.addEventListener("change", function () {
            porPagina = parseInt(selectRegistros.value, 10);
            paginaActual = 1;
            renderizar();
        });

        // Re-paginar cuando el buscador o filtro de estado cambia
        var inputBuscador = document.querySelector('[data-tabla-filtro="' + tablaId + '"]');
        var selectEstado = document.querySelector('[data-tabla-filtro-estado="' + tablaId + '"]');

        if (inputBuscador) {
            inputBuscador.addEventListener("input", function () {
                // Esperar a que tabla-filtro.js oculte/muestre las filas
                setTimeout(function () {
                    paginaActual = 1;
                    renderizar();
                }, 10);
            });
        }

        if (selectEstado) {
            selectEstado.addEventListener("change", function () {
                setTimeout(function () {
                    paginaActual = 1;
                    renderizar();
                }, 10);
            });
        }

        // Observar cambios en el ordenamiento (tabla-filtro.js reordena el DOM)
        var observer = new MutationObserver(function (mutations) {
            var reordenado = mutations.some(function (m) {
                return m.type === "childList" && m.target === tbody;
            });
            if (reordenado) {
                todasLasFilas = Array.from(tbody.querySelectorAll("tr"));
                renderizar();
            }
        });
        observer.observe(tbody, { childList: true });

        // ---------- Inicializar ----------
        renderizar();
    });
});
