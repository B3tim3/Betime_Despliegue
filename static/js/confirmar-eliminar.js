/*
 * Reemplaza el "¿Estás seguro?" feo del navegador por un modal de
 * SweetAlert2, para cualquier formulario de eliminar.
 *
 * Uso: envolver el botón "Eliminar" en un <form method="post"> con
 * data-confirmar-eliminar="mensaje a mostrar" en el propio <form>.
 * Este script intercepta el envío, muestra el modal, y solo si la
 * persona confirma, deja que el formulario se envíe de verdad.
 */

document.addEventListener("DOMContentLoaded", function () {

    if (typeof Swal === "undefined") {
        return;
    }

    document.querySelectorAll("[data-confirmar-eliminar]").forEach(function (form) {
        form.addEventListener("submit", function (evento) {
            evento.preventDefault();

            const mensaje = form.getAttribute("data-confirmar-eliminar");

            Swal.fire({
                title: "¿Estás seguro?",
                text: mensaje,
                icon: "warning",
                showCancelButton: true,
                confirmButtonText: "Sí, eliminar",
                cancelButtonText: "Cancelar",
                confirmButtonColor: "#dc3545",
                cancelButtonColor: "#6c757d",
            }).then(function (resultado) {
                if (resultado.isConfirmed) {
                    form.submit();
                }
            });
        });
    });

});
