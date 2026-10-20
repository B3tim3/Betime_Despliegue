/*
 * Agrega el ojito para mostrar/ocultar contraseña a CUALQUIER campo
 * de contraseña de la página, automáticamente -- no hace falta tocar
 * cada formulario (login, registro, recuperar contraseña, o
 * cualquiera que se agregue después) uno por uno.
 *
 * Busca todos los <input type="password"> que haya en la página, los
 * envuelve en un contenedor, y les pone un botón con el ícono del
 * ojo al lado derecho.
 */

document.addEventListener("DOMContentLoaded", function () {

    document.querySelectorAll('input[type="password"]').forEach(function (input) {

        // Por si este script llegara a correr más de una vez, no
        // envolver el mismo campo dos veces.
        if (input.closest(".mostrar-contrasena-wrapper")) {
            return;
        }

        const envoltorio = document.createElement("div");
        envoltorio.className = "mostrar-contrasena-wrapper";

        input.parentNode.insertBefore(envoltorio, input);
        envoltorio.appendChild(input);

        const boton = document.createElement("button");
        boton.type = "button";
        boton.className = "mostrar-contrasena-boton";
        boton.setAttribute("aria-label", "Mostrar contraseña");
        boton.innerHTML = '<i class="bi bi-eye"></i>';

        envoltorio.appendChild(boton);

        boton.addEventListener("click", function () {
            const estaOculta = input.type === "password";

            input.type = estaOculta ? "text" : "password";
            boton.innerHTML = estaOculta
                ? '<i class="bi bi-eye-slash"></i>'
                : '<i class="bi bi-eye"></i>';
            boton.setAttribute(
                "aria-label",
                estaOculta ? "Ocultar contraseña" : "Mostrar contraseña"
            );
        });
    });

});
