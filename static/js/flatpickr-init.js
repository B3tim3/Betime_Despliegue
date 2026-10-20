/*
 * Activa Flatpickr en cualquier input con la clase "flatpickr-fecha-hora"
 * (la pone el widget core.widgets.FlatpickrDateTimeInput).
 *
 * Flatpickr y su paquete de español ya se cargan desde base_private.html
 * antes que este archivo -- si no están disponibles, no hace nada (por
 * si alguna página los carga sin Flatpickr por error).
 */

document.addEventListener("DOMContentLoaded", function () {

    if (typeof flatpickr === "undefined") {
        return;
    }

    document.querySelectorAll(".flatpickr-fecha-hora").forEach(function (input) {
    flatpickr(input, {
        enableTime: true,
        dateFormat: "Y-m-d H:i",   // lo que se manda al servidor — sigue igual, no toca la BD
        altInput: true,
        altFormat: "d/m/Y h:i K",  // lo que VE la persona: ahora 12h con AM/PM
        time_24hr: false,
        locale: "es",
    });
});

});
