// Confirmación accesible compatible con el controlador global form_submit.js.
document.addEventListener('DOMContentLoaded', () => {
    const form = document.getElementById('edit-user-form');
    const modal = document.getElementById('confirmation-modal');
    const confirm = document.getElementById('confirm-save');
    const cancel = document.getElementById('cancel-save');
    const submit = document.getElementById('submit-edit-user');
    if (!form || !modal || !confirm || !cancel || !submit) return;

    let confirmed = false;
    let previousFocus = null;

    function openModal() {
        previousFocus = document.activeElement;
        modal.classList.remove('hidden');
        modal.classList.add('flex');
        confirm.focus();
    }
    function closeModal() {
        modal.classList.add('hidden');
        modal.classList.remove('flex');
        if (previousFocus && typeof previousFocus.focus === 'function') previousFocus.focus();
    }

    // Captura: impide que el controlador global considere el primer intento
    // un envío definitivo antes de que el usuario confirme.
    form.addEventListener('submit', (event) => {
        if (confirmed) return; // El segundo envío pasará por form_submit.js.
        event.preventDefault();
        event.stopImmediatePropagation();
        if (!form.reportValidity()) return;
        openModal();
    }, true);

    confirm.addEventListener('click', () => {
        if (confirmed || form.dataset.enviando === 'true') return;
        confirmed = true;
        closeModal();
        // requestSubmit conserva HTML5, CSRF y eventos submit.
        form.requestSubmit(submit);
        // Si una validación canceló el envío, permitir un nuevo intento.
        if (form.dataset.enviando !== 'true') confirmed = false;
    });

    cancel.addEventListener('click', closeModal);
    modal.addEventListener('click', (event) => {
        if (event.target === modal && !confirmed) closeModal();
    });
    modal.addEventListener('keydown', (event) => {
        if (event.key === 'Escape' && !confirmed) {
            event.preventDefault();
            closeModal();
        }
        if (event.key !== 'Tab') return;
        const targets = [cancel, confirm];
        const first = targets[0];
        const last = targets[targets.length - 1];
        if (event.shiftKey && document.activeElement === first) {
            event.preventDefault(); last.focus();
        } else if (!event.shiftKey && document.activeElement === last) {
            event.preventDefault(); first.focus();
        }
    });
    window.addEventListener('pageshow', () => {
        confirmed = false;
        modal.classList.add('hidden');
        modal.classList.remove('flex');
    });
});