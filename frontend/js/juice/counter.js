/**
 * Spring-physics number displays.
 *
 * Ported from pygame_ui/components/counter.py (AnimatedCounter): the shown
 * value chases the target on a spring, so bankroll and count changes crunch
 * satisfyingly instead of snapping.
 */

import { onFrame, reducedMotion } from './loop.js';
import { Spring } from './tween.js';

export function attachCounter(el, { format = v => Math.round(v).toString(), flashClass = null } = {}) {
    const spring = new Spring(parseFloat(el.textContent) || 0);
    let unsubscribe = null;

    function step(dt) {
        const settled = spring.step(dt);
        el.textContent = format(spring.value);
        if (settled) {
            unsubscribe?.();
            unsubscribe = null;
        }
    }

    return {
        set(value, { instant = false } = {}) {
            if (instant || reducedMotion.matches) {
                spring.value = value;
                spring.target = value;
                spring.velocity = 0;
                el.textContent = format(value);
                return;
            }
            if (value === spring.target) return;

            if (flashClass) {
                el.classList.remove(flashClass);
                void el.offsetWidth; // restart the animation
                el.classList.add(flashClass);
            }
            spring.target = value;
            if (!unsubscribe) unsubscribe = onFrame(step);
        },
        get value() {
            return spring.target;
        },
    };
}
