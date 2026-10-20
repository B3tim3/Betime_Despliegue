/*
 * Utilidades de tabla reutilizables — JS puro, sin librerías.
 *
 * 1) BUSCADOR EN VIVO
 *      <input data-tabla-filtro="id-tabla" ...>
 *      (opcional) <select data-tabla-filtro-estado="id-tabla">
 *      cada <tr> del <tbody> con data-estado="valor" (si usas el select)
 *
 * 2) ORDENAR AL HACER CLIC EN EL ENCABEZADO
 *      <table id="id-tabla" data-tabla-ordenable>
 *      cada <th> que se pueda ordenar:
 *          data-ordenar-columna="0"   (índice de la columna, empieza en 0)
 *          data-ordenar-tipo="texto"  (o "numero" o "fecha" — opcional, default texto)
 *
 * 3) QUE "EXPORTAR" RESPETE LO BUSCADO
 *      Los enlaces de exportar (components/exportar/botones.html) llevan
 *      data-export-para="id-tabla" — cuando escribes en el buscador o
 *      cambias el filtro de estado de esa tabla, este script actualiza
 *      esos enlaces para que el archivo exportado traiga lo mismo que
 *      ves filtrado en pantalla, no todos los registros.
 */

document.addEventListener("DOMContentLoaded", function () {

    // ---------- 1) Buscador + filtro de estado + sincronizar exportar ----------

    document.querySelectorAll("[data-tabla-filtro]").forEach(function (input) {
        const tablaId = input.getAttribute("data-tabla-filtro");
        const tabla = document.getElementById(tablaId);

        if (!tabla) {
            return;
        }

        const filas = tabla.querySelectorAll("tbody tr");
        const selectEstado = document.querySelector('[data-tabla-filtro-estado="' + tablaId + '"]');
        const enlacesExportar = document.querySelectorAll('[data-export-para="' + tablaId + '"]');

        function actualizarFiltro() {
            const texto = input.value.trim().toLowerCase();
            const estado = selectEstado ? selectEstado.value : "";

            filas.forEach(function (fila) {
                const coincideTexto = texto === "" || fila.textContent.toLowerCase().includes(texto);
                const coincideEstado = estado === "" || fila.getAttribute("data-estado") === estado;
                fila.style.display = (coincideTexto && coincideEstado) ? "" : "none";
            });
        }

        function actualizarEnlacesExportar() {
            if (enlacesExportar.length === 0) {
                return;
            }

            const texto = input.value.trim();
            const estado = selectEstado ? selectEstado.value : "";

            enlacesExportar.forEach(function (enlace) {
                const url = new URL(enlace.href, window.location.origin);

                if (texto) {
                    url.searchParams.set("q", texto);
                } else {
                    url.searchParams.delete("q");
                }

                if (estado) {
                    url.searchParams.set("estado", estado);
                } else {
                    url.searchParams.delete("estado");
                }

                enlace.href = url.pathname + "?" + url.searchParams.toString();
            });
        }

        function actualizar() {
            actualizarFiltro();
            actualizarEnlacesExportar();
        }

        input.addEventListener("input", actualizar);

        if (selectEstado) {
            selectEstado.addEventListener("change", actualizar);
        }

        // Deja la tabla y los enlaces de exportar sincronizados desde que
        // carga la página — importante porque el navegador a veces
        // restaura texto que quedó escrito en el buscador (al volver
        // atrás, por ejemplo). Si solo actualizáramos el exportar y no
        // la tabla, se verían todas las filas en pantalla pero el
        // archivo exportado saldría filtrado (y probablemente vacío)
        // por un texto que ni se nota que sigue ahí.
        actualizar();
    });

    // ---------- 2) Ordenar al hacer clic en el encabezado ----------

    function parsearFecha(texto) {
        // admite "dd/mm/aaaa" y "dd/mm/aaaa hh:mm"
        const partes = texto.split(" ");
        const fecha = partes[0].split("/");
        const hora = partes[1] || "00:00";
        if (fecha.length !== 3) {
            return new Date(0);
        }
        return new Date(fecha[2] + "-" + fecha[1] + "-" + fecha[0] + "T" + hora);
    }

    document.querySelectorAll("table[data-tabla-ordenable]").forEach(function (tabla) {
        const encabezados = tabla.querySelectorAll("th[data-ordenar-columna]");

        encabezados.forEach(function (th) {
            th.style.cursor = "pointer";
            th.style.userSelect = "none";

            const indicador = document.createElement("span");
            indicador.className = "ms-1";
            th.appendChild(indicador);

            let ascendente = true;

            th.addEventListener("click", function () {
                const columna = parseInt(th.getAttribute("data-ordenar-columna"), 10);
                const tipo = th.getAttribute("data-ordenar-tipo") || "texto";
                const cuerpo = tabla.querySelector("tbody");
                const filas = Array.from(cuerpo.querySelectorAll("tr"));

                filas.sort(function (filaA, filaB) {
                    let valorA = filaA.children[columna].textContent.trim();
                    let valorB = filaB.children[columna].textContent.trim();

                    if (tipo === "numero") {
                        const numeroA = parseFloat(valorA.replace(/[^0-9.-]/g, "")) || 0;
                        const numeroB = parseFloat(valorB.replace(/[^0-9.-]/g, "")) || 0;
                        return ascendente ? numeroA - numeroB : numeroB - numeroA;
                    }

                    if (tipo === "fecha") {
                        const fechaA = parsearFecha(valorA);
                        const fechaB = parsearFecha(valorB);
                        return ascendente ? fechaA - fechaB : fechaB - fechaA;
                    }

                    valorA = valorA.toLowerCase();
                    valorB = valorB.toLowerCase();
                    if (valorA < valorB) return ascendente ? -1 : 1;
                    if (valorA > valorB) return ascendente ? 1 : -1;
                    return 0;
                });

                encabezados.forEach(function (otro) {
                    otro.querySelector("span").textContent = "";
                });
                indicador.textContent = ascendente ? " \u25b2" : " \u25bc";

                filas.forEach(function (fila) {
                    cuerpo.appendChild(fila);
                });

                ascendente = !ascendente;
            });
        });
    });

});
