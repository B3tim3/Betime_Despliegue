/*
 * Lector de QR de Be Time (lo usan el escáner de actividades y el de actividades por mérito).
 *
 * Por qué existe: el widget "Html5QrcodeScanner" que se usaba antes mostraba su propia
 * pantalla de permisos y un selector de cámara que había que tocar cada vez (y en el
 * celular solía arrancar con la frontal). Aquí se usa la clase base "Html5Qrcode":
 *   - al pulsar «Escanear» el navegador pide el permiso de cámara (si falta) y abre
 *     DIRECTAMENTE la cámara trasera (facingMode "environment");
 *   - «Cambiar cámara» solo aparece si el dispositivo tiene más de una;
 *   - «Detener» apaga la cámara (y se apaga sola al salir de la página).
 * Si el dispositivo solo tiene una cámara (p. ej. un portátil), el navegador usa esa.
 *
 * Uso (la plantilla components/lector_qr.html trae el HTML necesario):
 *     iniciarLectorQR(function (textoDelQR) { ... });
 * Requiere la librería html5-qrcode cargada antes.
 */
(function () {
    "use strict";

    function porId(id) { return document.getElementById(id); }

    // Navegadores "integrados" (WhatsApp, Instagram, Facebook, Telegram...) suelen bloquear la cámara,
    // sobre todo en iPhone: hay que abrir el enlace en Safari / Chrome.
    function esNavegadorIntegrado() {
        return /FBAN|FBAV|Instagram|WhatsApp|Line\/|MicroMessenger|Telegram|Snapchat|; wv\)/i.test(navigator.userAgent || "");
    }

    function mensajeError(error) {
        var texto = String(error && (error.name || error.message) ? (error.name + " " + error.message) : error);
        if (!window.isSecureContext) {
            return "La cámara solo funciona en una conexión segura (https). Abre Be Time con su dirección https.";
        }
        if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
            return esNavegadorIntegrado()
                ? "Este navegador integrado no permite usar la cámara. Abre el enlace en Safari o Chrome."
                : "Este navegador no permite usar la cámara. Prueba con Safari o Chrome actualizados.";
        }
        if (/NotAllowed|Permission|denied/i.test(texto)) {
            return "No hay permiso para usar la cámara. Actívalo desde el candado de la barra de direcciones y vuelve a pulsar «Escanear».";
        }
        if (/NotFound|Requested device not found|no camera/i.test(texto)) {
            return "No se encontró ninguna cámara en este dispositivo.";
        }
        if (/NotReadable|TrackStart|in use/i.test(texto)) {
            return "La cámara está siendo usada por otra aplicación. Ciérrala e inténtalo de nuevo.";
        }
        return "No se pudo abrir la cámara (" + texto.trim().slice(0, 80) + "). Inténtalo de nuevo o escanea el QR con la app de Cámara del celular.";
    }

    window.iniciarLectorQR = function (alLeer) {
        var estado = porId("lector-qr-estado");
        var portada = porId("lector-portada");
        var visor = porId("lector-qr");
        var controles = porId("lector-controles");
        var botonIniciar = porId("lector-iniciar");
        var botonDetener = porId("lector-detener");
        var botonCambiar = porId("lector-cambiar");

        if (typeof Html5Qrcode === "undefined") {
            estado.textContent = "No se pudo cargar el lector de QR (revisa tu conexión a internet).";
            botonIniciar.disabled = true;
            return;
        }

        var lector = null;
        var activo = false;
        var ocupado = false;
        var camaraActual = "environment";       // trasera primero

        function mostrar(camaraEncendida) {
            portada.hidden = camaraEncendida;
            visor.hidden = !camaraEncendida;
            controles.hidden = !camaraEncendida;
        }

        // Recuadro de lectura: ~70 % del lado menor del video, entre 180 y 320 px.
        function recuadro(ancho, alto) {
            var lado = Math.floor(Math.min(ancho, alto) * 0.7);
            lado = Math.max(180, Math.min(320, lado));
            return { width: lado, height: lado };
        }

        function arrancar(facingMode) {
            if (ocupado || activo) { return Promise.resolve(); }
            ocupado = true;
            botonIniciar.disabled = true;
            estado.textContent = "Abriendo cámara...";
            mostrar(true);      // el visor debe estar visible para que la librería mida su ancho

            if (!lector) {
                lector = new Html5Qrcode("lector-qr", {
                    verbose: false,
                    formatsToSupport: [Html5QrcodeSupportedFormats.QR_CODE],
                });
            }

            // Vigilante: si pasan 8 s y no hay imagen (permiso sin responder, cámara ocupada...),
            // se avisa con pistas en vez de dejar la pantalla en "Abriendo cámara...".
            var vigilante = setTimeout(function () {
                var video = visor.querySelector("video");
                if (!activo || !video || !video.videoWidth) {
                    estado.textContent = esNavegadorIntegrado()
                        ? "La cámara no responde. Abre este enlace en Safari o Chrome (no dentro de WhatsApp u otra app)."
                        : "La cámara no responde. Revisa el permiso de cámara del navegador y que ninguna otra app la esté usando.";
                }
            }, 8000);

            return lector.start(
                { facingMode: facingMode },
                { fps: 10, qrbox: recuadro },
                function (texto) { alLeer(texto); },
                function () { /* fotogramas sin QR: se ignoran */ }
            ).then(function () {
                activo = true;
                camaraActual = facingMode;
                estado.textContent = "Apunta al código QR.";
                // OJO: NO usar Html5Qrcode.getCameras() aquí. Esa función pide la cámara OTRA vez y, en
                // iPhone (Safari solo permite una captura a la vez), congela o cierra el video que acaba
                // de abrirse. enumerateDevices() solo lista dispositivos, sin abrir ninguno.
                botonCambiar.hidden = true;
                if (navigator.mediaDevices && navigator.mediaDevices.enumerateDevices) {
                    return navigator.mediaDevices.enumerateDevices().then(function (lista) {
                        var camaras = lista.filter(function (d) { return d.kind === "videoinput"; });
                        botonCambiar.hidden = camaras.length < 2;
                    }).catch(function () { /* sin botón de cambiar */ });
                }
            }).catch(function (error) {
                mostrar(false);
                estado.textContent = mensajeError(error);
            }).then(function () {
                clearTimeout(vigilante);
                ocupado = false;
                botonIniciar.disabled = false;
            });
        }

        function detener() {
            if (!lector || !activo) { return Promise.resolve(); }
            return lector.stop().catch(function () {}).then(function () {
                try { lector.clear(); } catch (e) { /* ya estaba limpio */ }
                activo = false;
                mostrar(false);
            });
        }

        botonIniciar.addEventListener("click", function () { arrancar("environment"); });

        botonDetener.addEventListener("click", function () {
            detener().then(function () { estado.textContent = "Cámara apagada. Pulsa «Escanear» para continuar."; });
        });

        botonCambiar.addEventListener("click", function () {
            var siguiente = camaraActual === "environment" ? "user" : "environment";
            detener().then(function () { return arrancar(siguiente); });
        });

        // Apaga la cámara al salir de la página (la luz de la cámara no debe quedar encendida).
        window.addEventListener("pagehide", detener);

        mostrar(false);
    };
})();
