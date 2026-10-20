/* Control visual de inactividad. Flask decide si la sesión sigue vigente. */
(() => {
    'use strict';

    document.addEventListener('DOMContentLoaded', () => {
        const config = document.getElementById('config-sesion');
        const modal = document.getElementById('modal-inactividad');
        const mantener = document.getElementById('btn-mantener-sesion');
        const contador = document.getElementById('contador-expiracion');
        const logoutForm = document.getElementById('form-logout-inactividad');
        if (!config || !modal || !mantener || !contador || !logoutForm) return;

        const advertenciaMs = Number(config.dataset.advertenciaSegundos || 120) * 1000;
        const tiempoEntreRenovacionesMs = 45 * 1000;
        let expiraEn = null;
        let ultimoEnvio = Date.now();
        let renovando = false;
        let finalizando = false;
        let actividadReciente = false;

        function irAlLogin() {
            if (finalizando) return;
            finalizando = true;
            window.location.assign(config.dataset.loginUrl);
        }

        function finalizarSesion() {
            if (finalizando) return;
            finalizando = true;
            // Un POST con CSRF solicita el cierre; si Flask ya expiró,
            // before_request redirigirá igualmente al login.
            logoutForm.submit();
        }

        function actualizarVencimiento(segundos) {
            expiraEn = Date.now() + Math.max(0, segundos) * 1000;
            ultimoEnvio = Date.now();
            actividadReciente = false;
            modal.classList.add('hidden');
            mantener.disabled = false;
            mantener.textContent = 'Permanecer Conectado';
        }

        async function solicitud(url, metodo = 'GET') {
            const opciones = {
                method: metodo,
                credentials: 'same-origin',
                cache: 'no-store',
                headers: { 'Accept': 'application/json' }
            };
            if (metodo === 'POST') {
                opciones.headers['X-CSRFToken'] = config.dataset.csrf;
            }
            const respuesta = await fetch(url, opciones);
            if (!respuesta.ok || !respuesta.headers.get('Content-Type')?.includes('application/json')) {
                if (respuesta.status === 401 || respuesta.redirected) irAlLogin();
                throw new Error(`No se pudo comprobar la sesión (${respuesta.status})`);
            }
            const datos = await respuesta.json();
            if (!datos.autenticado) {
                irAlLogin();
                throw new Error('Sesión no válida');
            }
            return datos;
        }

        async function renovar(explicita = false) {
            if (renovando || finalizando) return;
            if (!explicita && (!modal.classList.contains('hidden') || !actividadReciente)) return;
            renovando = true;
            if (explicita) {
                mantener.disabled = true;
                mantener.textContent = 'Comprobando...';
            }
            try {
                const datos = await solicitud(config.dataset.renovarUrl, 'POST');
                actualizarVencimiento(datos.restante_segundos);
            } catch (error) {
                console.warn(error);
                if (explicita && !finalizando) {
                    mantener.disabled = false;
                    mantener.textContent = 'Reintentar';
                }
                // Ante fallos de red no se presupone que la sesión fue renovada.
            } finally {
                renovando = false;
            }
        }

        function registrarActividad() {
            if (finalizando || !modal.classList.contains('hidden')) return;
            actividadReciente = true;
            // Solo actividad real del usuario puede iniciar un POST de renovación.
            // Los eventos frecuentes no generan una petición por movimiento.
            if (Date.now() - ultimoEnvio >= tiempoEntreRenovacionesMs) {
                renovar();
            }
        }

        ['pointerdown', 'keydown', 'scroll', 'touchstart'].forEach(evento => {
            document.addEventListener(evento, registrarActividad, { passive: true });
        });
        // Para una escritura continua, no depende de clics de ratón.
        document.addEventListener('input', registrarActividad, { passive: true });

        mantener.addEventListener('click', () => renovar(true));

        function actualizarPantalla() {
            if (finalizando || expiraEn === null) return;
            const restantes = Math.max(0, Math.ceil((expiraEn - Date.now()) / 1000));
            if (restantes <= 0) {
                finalizarSesion();
                return;
            }
            if (restantes * 1000 <= advertenciaMs) {
                modal.classList.remove('hidden');
                contador.textContent = `${String(Math.floor(restantes / 60)).padStart(2, '0')}:${String(restantes % 60).padStart(2, '0')}`;
            } else {
                modal.classList.add('hidden');
            }
        }

        async function consultarEstado() {
            if (finalizando) return;
            try {
                const datos = await solicitud(config.dataset.estadoUrl);
                actualizarVencimiento(datos.restante_segundos);
                actualizarPantalla();
            } catch (error) {
                console.warn(error);
            }
        }

        // Nunca renovamos por cargar la página, cambiar de pestaña o mediante sondeos.
        document.addEventListener('visibilitychange', () => {
            if (!document.hidden) consultarEstado();
        });
        window.addEventListener('pageshow', (evento) => {
            if (evento.persisted) consultarEstado();
        });
        setInterval(actualizarPantalla, 1000);
        consultarEstado();
    });
})();