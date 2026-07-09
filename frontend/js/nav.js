/**
 * Screen switching, importable from any module without cycles.
 */

import { appState } from './state.js';

const SECTIONS = {
    'play': 'game-area',
    'count-drill': 'count-drill-area',
    'strategy-drill': 'strategy-drill-area',
    'performance': 'performance-area',
    'profile': 'profile-area',
    'daily': 'daily-area',
};

const enterHooks = {};

export function onEnter(mode, fn) {
    enterHooks[mode] = fn;
}

export function switchMode(mode) {
    appState.mode = mode;

    document.querySelectorAll('footer nav a').forEach(a => a.classList.remove('active'));
    document.getElementById(`nav-${mode}`)?.classList.add('active');

    for (const [name, sectionId] of Object.entries(SECTIONS)) {
        document.getElementById(sectionId)?.classList.toggle('hidden', name !== mode);
    }

    enterHooks[mode]?.();
}
