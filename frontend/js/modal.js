/**
 * Shared modal accessibility: focus trap, Escape-to-close, focus-return.
 *
 * One implementation instead of repeating the pattern per screen. Every
 * modal in the app (strategy chart, settings, count check-in, daily
 * result, onboarding) opens and closes through this.
 */

const FOCUSABLE = 'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])';

const openState = new WeakMap(); // el -> { trigger, keydownHandler, onClose }

function focusableIn(el) {
    return [...el.querySelectorAll(FOCUSABLE)].filter(
        (n) => !n.disabled && n.offsetParent !== null
    );
}

/**
 * Show a modal: remember what had focus, move focus inside, trap Tab, and
 * (unless escapable is false) close on Escape.
 */
export function openModal(el, { onClose, escapable = true } = {}) {
    if (!el || !el.classList.contains('hidden')) return;

    const trigger = document.activeElement;
    el.classList.remove('hidden');

    const first = focusableIn(el)[0];
    (first || el).focus?.();

    const keydownHandler = (e) => {
        if (e.key === 'Escape') {
            if (escapable) {
                e.preventDefault();
                closeModal(el);
            }
            return;
        }
        if (e.key !== 'Tab') return;

        const items = focusableIn(el);
        if (items.length === 0) return;
        const firstItem = items[0];
        const lastItem = items[items.length - 1];

        if (e.shiftKey && document.activeElement === firstItem) {
            e.preventDefault();
            lastItem.focus();
        } else if (!e.shiftKey && document.activeElement === lastItem) {
            e.preventDefault();
            firstItem.focus();
        }
    };
    document.addEventListener('keydown', keydownHandler);

    openState.set(el, { trigger, keydownHandler, onClose });
}

/**
 * Hide a modal, drop its keyboard trap, and return focus to whatever
 * opened it.
 */
export function closeModal(el) {
    if (!el || el.classList.contains('hidden')) return;
    el.classList.add('hidden');

    const s = openState.get(el);
    if (s) {
        document.removeEventListener('keydown', s.keydownHandler);
        openState.delete(el);
        s.trigger?.focus?.();
        s.onClose?.();
    }
}

/** Click on the backdrop (not the content) closes the modal. */
export function bindBackdropClose(el) {
    el?.addEventListener('click', (e) => {
        if (e.target === el) closeModal(el);
    });
}
