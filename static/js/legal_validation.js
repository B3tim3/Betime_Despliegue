/**
 * legal_validation.js
 * Validación del lado del cliente para los checkboxes legales
 * en el formulario de registro de Be Time.
 *
 * INSTRUCCIONES:
 *   Incluir este script en la plantilla de registro (registro.html)
 *   justo antes de </body> o dentro de {% block extra_js %}:
 *
 *   <script src="{% static 'js/legal_validation.js' %}"></script>
 */
document.addEventListener("DOMContentLoaded", function () {
    "use strict";

    var form = document.querySelector("form");
    if (!form) return;

    var checkTerminos = document.getElementById("acepta_terminos");
    var checkDatos    = document.getElementById("acepta_datos");

    if (!checkTerminos || !checkDatos) return;

    form.addEventListener("submit", function (e) {
        var valido = true;

        if (!checkTerminos.checked) {
            checkTerminos.classList.add("is-invalid");
            valido = false;
        } else {
            checkTerminos.classList.remove("is-invalid");
        }

        if (!checkDatos.checked) {
            checkDatos.classList.add("is-invalid");
            valido = false;
        } else {
            checkDatos.classList.remove("is-invalid");
        }

        if (!valido) {
            e.preventDefault();
            // Scroll al primer checkbox inválido
            var primerInvalido = form.querySelector(".is-invalid");
            if (primerInvalido) {
                primerInvalido.scrollIntoView({ behavior: "smooth", block: "center" });
            }
        }
    });

    // Quitar estado inválido al marcar
    [checkTerminos, checkDatos].forEach(function (cb) {
        cb.addEventListener("change", function () {
            if (this.checked) {
                this.classList.remove("is-invalid");
            }
        });
    });
});
