/*
 * Tablas del panel en el celular.
 *
 * En pantallas angostas las tablas se muestran como TARJETAS (el CSS está
 * en static/css/responsive.css). Para eso cada celda necesita saber cómo se
 * llama su columna: este script lo copia del encabezado a data-label. Hace
 * lo mismo en todas las tablas que viven dentro de un ".table-responsive",
 * incluida la de django-tables2, sin tener que tocar cada plantilla.
 *
 * - Una tabla puede excluirse con el atributo data-sin-tarjetas.
 * - La columna de botones (la que se llama "Acciones" o no tiene nombre
 *   y trae botones) se marca como .celda-acciones.
 * - No cambia el contenido de las celdas: el buscador (tabla-filtro.js) y
 *   el ordenamiento siguen funcionando igual.
 */
document.addEventListener("DOMContentLoaded", function () {
    document.querySelectorAll(".table-responsive table").forEach(function (tabla) {
        if (tabla.hasAttribute("data-sin-tarjetas")) {
            return;
        }

        const encabezados = Array.from(tabla.querySelectorAll("thead th")).map(function (th) {
            return th.textContent.replace(/\s+/g, " ").trim();
        });

        tabla.querySelectorAll("tbody tr").forEach(function (fila) {
            Array.from(fila.children).forEach(function (celda, i) {
                const nombre = encabezados[i] || "";
                celda.setAttribute("data-label", nombre);

                const esAcciones = /^acciones$/i.test(nombre) ||
                    (nombre === "" && celda.querySelector(".btn"));
                if (esAcciones) {
                    celda.classList.add("celda-acciones");
                }
            });
        });

        tabla.classList.add("tabla-cards");
    });
});
