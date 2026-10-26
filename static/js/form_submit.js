/* Previene dobles POST normales sin intervenir búsquedas GET ni formularios inválidos. */
document.addEventListener('DOMContentLoaded', () => {
    document.querySelectorAll('form').forEach((formulario) => {
        if (formulario.method.toUpperCase() !== 'POST') return;
        formulario.addEventListener('submit', (evento) => {
            if (evento.defaultPrevented) return;
            if (!formulario.checkValidity()) return;
            if (formulario.dataset.enviando === 'true') {
                evento.preventDefault();
                return;
            }
            formulario.dataset.enviando = 'true';
            const boton = evento.submitter || formulario.querySelector('button[type="submit"]');
            if (!boton) return;
            // No deshabilitar el botón antes del envío: podría excluirse su name/value.
            boton.setAttribute('aria-disabled', 'true');
            boton.classList.add('opacity-75', 'cursor-wait');
            // Recuperación al volver con el historial del navegador (bfcache).
        });
    });
    window.addEventListener('pageshow', () => {
        document.querySelectorAll('form[data-enviando="true"]').forEach((formulario) => {
            formulario.dataset.enviando = 'false';
            formulario.querySelectorAll('[aria-disabled="true"]').forEach((boton) => {
                boton.removeAttribute('aria-disabled');
                boton.classList.remove('opacity-75', 'cursor-wait');
            });
        });
    });
});
