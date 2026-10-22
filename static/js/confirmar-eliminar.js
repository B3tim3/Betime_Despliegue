/*
 * Reemplaza el "¿Estás seguro?" feo del navegador por un modal de
 * SweetAlert2, para cualquier formulario de eliminar.
 *
 * Uso: envolver el botón "Eliminar" en un <form method="post"> con
 * data-confirmar-eliminar="mensaje a mostrar" en el propio <form>.
 * Opcionales en el mismo <form>: data-confirmar-titulo, data-confirmar-boton
 * y data-confirmar-volver para cambiar los textos del modal (por ejemplo
 * al cancelar una inscripción, donde "Sí, eliminar" no tiene sentido).
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
                title: form.getAttribute("data-confirmar-titulo") || "¿Estás seguro?",
                text: mensaje,
                icon: "warning",
                showCancelButton: true,
                confirmButtonText: form.getAttribute("data-confirmar-boton") || "Sí, eliminar",
                cancelButtonText: form.getAttribute("data-confirmar-volver") || "Cancelar",
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
