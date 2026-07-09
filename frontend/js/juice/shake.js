/**
 * Trauma-based screen shake.
 *
 * Ported from pygame_ui/effects/screen_shake.py (Eiserloh GDC model):
 * shake intensity = trauma², decayed linearly, sampled with offset sine
 * noise so x/y/rotation drift independently.
 */

import { onFrame, reducedMotion } from './loop.js';

export const SHAKE = {
    LIGHT: 0.2,
    MEDIUM: 0.35,
    HEAVY: 0.5,
    IMPACT: 0.65,
};

const MAX_OFFSET = 9;      // px
const MAX_ROTATION = 0.7;  // deg
const DECAY = 1.4;         // trauma per second

let trauma = 0;
let unsubscribe = null;
let target = null;

function step(dt, now) {
    trauma = Math.max(0, trauma - DECAY * dt);
    const shake = trauma * trauma;

    if (!target) target = document.getElementById('table-felt');
    if (!target) return;

    if (shake <= 0.0005) {
        target.style.transform = '';
        unsubscribe?.();
        unsubscribe = null;
        return;
    }

    const t = now / 1000;
    const dx = MAX_OFFSET * shake * Math.sin(t * 57.3 + 1.3);
    const dy = MAX_OFFSET * shake * Math.sin(t * 61.7 + 4.1);
    const rot = MAX_ROTATION * shake * Math.sin(t * 53.9 + 2.2);
    target.style.transform = `translate(${dx.toFixed(2)}px, ${dy.toFixed(2)}px) rotate(${rot.toFixed(3)}deg)`;
}

/**
 * Add trauma (0..1). Use the SHAKE presets.
 */
export function addShake(amount) {
    if (reducedMotion.matches) return;
    trauma = Math.min(1, trauma + amount);
    if (!unsubscribe) {
        unsubscribe = onFrame(step);
    }
}
