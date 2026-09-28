/**
 * First-run onboarding: route new players to the right starting point.
 */

import { switchMode } from '../nav.js';
import { openModal, closeModal, bindBackdropClose } from '../modal.js';

const FLAG = 'bjt-onboarded';

export function maybeShowOnboarding() {
    if (localStorage.getItem(FLAG)) return;
    const modal = document.getElementById('onboarding-modal');
    // Dismissing without picking a path (Escape/backdrop) still marks the
    // player onboarded — it behaves like "just deal".
    openModal(modal, { onClose: () => localStorage.setItem(FLAG, '1') });
}

export function initOnboarding() {
    const modal = document.getElementById('onboarding-modal');
    if (!modal) return;

    bindBackdropClose(modal);

    const done = (mode) => {
        closeModal(modal); // invokes the onClose registered in maybeShowOnboarding
        if (mode) switchMode(mode);
    };

    document.getElementById('onboard-new')?.addEventListener('click', () => done('academy'));
    document.getElementById('onboard-knows')?.addEventListener('click', () => done('academy'));
    document.getElementById('onboard-deal')?.addEventListener('click', () => done('play'));
}
