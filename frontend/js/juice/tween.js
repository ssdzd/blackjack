/**
 * Easing + tween engine.
 *
 * Ported from pygame_ui/core/animation.py — same easing math, driven by the
 * shared rAF loop instead of a game tick.
 */

import { onFrame, reducedMotion } from './loop.js';

export const easings = {
    linear: t => t,
    easeInQuad: t => t * t,
    easeOutQuad: t => t * (2 - t),
    easeInOutQuad: t => (t < 0.5 ? 2 * t * t : -1 + (4 - 2 * t) * t),
    easeOutCubic: t => 1 + (--t) * t * t,
    easeOutBack: t => {
        const c1 = 1.70158;
        const c3 = c1 + 1;
        return 1 + c3 * Math.pow(t - 1, 3) + c1 * Math.pow(t - 1, 2);
    },
    easeOutElastic: t => {
        if (t === 0 || t === 1) return t;
        const c4 = (2 * Math.PI) / 3;
        return Math.pow(2, -10 * t) * Math.sin((t * 10 - 0.75) * c4) + 1;
    },
    easeOutBounce: t => {
        const n1 = 7.5625;
        const d1 = 2.75;
        if (t < 1 / d1) return n1 * t * t;
        if (t < 2 / d1) return n1 * (t -= 1.5 / d1) * t + 0.75;
        if (t < 2.5 / d1) return n1 * (t -= 2.25 / d1) * t + 0.9375;
        return n1 * (t -= 2.625 / d1) * t + 0.984375;
    },
};

/**
 * Animate a number (or array of numbers) over time.
 * Returns a cancel function.
 */
export function tween({ from, to, duration = 300, ease = easings.easeOutCubic, onUpdate, onComplete }) {
    if (reducedMotion.matches) {
        onUpdate?.(to);
        onComplete?.();
        return () => {};
    }

    const isArray = Array.isArray(from);
    let elapsed = 0;

    const stop = onFrame(dt => {
        elapsed += dt * 1000;
        const t = Math.min(elapsed / duration, 1);
        const k = ease(t);

        if (isArray) {
            onUpdate?.(from.map((f, i) => f + (to[i] - f) * k));
        } else {
            onUpdate?.(from + (to - from) * k);
        }

        if (t >= 1) {
            stop();
            onComplete?.();
        }
    });

    return stop;
}

/**
 * Critically-damped-ish spring integrator for one value.
 * Call step(dt) each frame; read .value.
 */
export class Spring {
    constructor(value = 0, { stiffness = 170, damping = 26 } = {}) {
        this.value = value;
        this.target = value;
        this.velocity = 0;
        this.stiffness = stiffness;
        this.damping = damping;
    }

    step(dt) {
        const displacement = this.target - this.value;
        const accel = this.stiffness * displacement - this.damping * this.velocity;
        this.velocity += accel * dt;
        this.value += this.velocity * dt;

        if (Math.abs(displacement) < 0.001 && Math.abs(this.velocity) < 0.001) {
            this.value = this.target;
            this.velocity = 0;
            return true; // settled
        }
        return false;
    }
}

/** Promise that resolves after ms (0 under reduced motion). */
export function wait(ms) {
    if (reducedMotion.matches) return Promise.resolve();
    return new Promise(resolve => setTimeout(resolve, ms));
}
