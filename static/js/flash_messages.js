/* Notificaciones reutilizables: todas se cierran automáticamente o a petición del usuario. */
document.addEventListener('DOMContentLoaded', () => {
    const reducirMovimiento = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

    document.querySelectorAll('.flash-message').forEach((mensaje) => {
        const categoria = mensaje.dataset.flashCategory;
        const duracionMs = categoria === 'danger' ? 7000 : 5000;
        let cerrando = false;
        let temporizador = null;

        function cerrar() {
            if (cerrando) return;
            cerrando = true;
            window.clearTimeout(temporizador);

            if (reducirMovimiento) {
                mensaje.remove();
                return;
            }

            mensaje.classList.add('fade-out');
            mensaje.addEventListener('animationend', (evento) => {
                if (evento.target === mensaje) mensaje.remove();
            }, { once: true });
            // Respaldo si la animación no llega a disparar su evento.
            window.setTimeout(() => mensaje.remove(), 700);
        }

        const boton = mensaje.querySelector('button[aria-label="Cerrar notificación"]');
        if (boton) boton.addEventListener('click', cerrar);
        temporizador = window.setTimeout(cerrar, duracionMs);
    });
});
