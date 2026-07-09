/**
 * First-run onboarding: route new players to the right starting point.
 */

import { switchMode } from '../nav.js';

const FLAG = 'bjt-onboarded';

export function maybeShowOnboarding() {
    if (localStorage.getItem(FLAG)) return;
    document.getElementById('onboarding-modal')?.classList.remove('hidden');
}

export function initOnboarding() {
    const modal = document.getElementById('onboarding-modal');
    if (!modal) return;

    const done = (mode) => {
        localStorage.setItem(FLAG, '1');
        modal.classList.add('hidden');
        if (mode) switchMode(mode);
    };

    document.getElementById('onboard-new')?.addEventListener('click', () => done('academy'));
    document.getElementById('onboard-knows')?.addEventListener('click', () => done('academy'));
    document.getElementById('onboard-deal')?.addEventListener('click', () => done('play'));
}
