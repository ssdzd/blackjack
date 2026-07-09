/**
 * Queued toast notifications.
 *
 * Slides in at the top-right, away from the cards (the vision doc's rule:
 * feedback never covers the table).
 */

const MAX_VISIBLE = 4;

function layer() {
    let el = document.getElementById('toast-layer');
    if (!el) {
        el = document.createElement('div');
        el.id = 'toast-layer';
        document.body.appendChild(el);
    }
    return el;
}

/**
 * Show a toast. Variants: 'info' | 'gold' | 'danger'.
 */
export function toast(message, { variant = 'info', duration = 2600, title = null } = {}) {
    const host = layer();

    while (host.children.length >= MAX_VISIBLE) {
        host.firstElementChild.remove();
    }

    const el = document.createElement('div');
    el.className = `toast toast-${variant}`;
    if (title) {
        const t = document.createElement('div');
        t.className = 'toast-title';
        t.textContent = title;
        el.appendChild(t);
    }
    const body = document.createElement('div');
    body.className = 'toast-body';
    body.textContent = message;
    el.appendChild(body);

    host.appendChild(el);
    requestAnimationFrame(() => el.classList.add('toast-in'));

    setTimeout(() => {
        el.classList.remove('toast-in');
        el.classList.add('toast-out');
        setTimeout(() => el.remove(), 350);
    }, duration);

    return el;
}
