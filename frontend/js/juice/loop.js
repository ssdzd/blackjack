/**
 * Single shared requestAnimationFrame loop.
 *
 * Everything animated (tweens, springs, particles, shake) subscribes here;
 * nothing else in the app calls requestAnimationFrame. The loop stops itself
 * when the last subscriber leaves.
 */

const subscribers = new Set();
let running = false;
let last = 0;

function frame(now) {
    // Clamp dt so a background tab doesn't produce a giant catch-up step
    const dt = Math.min((now - last) / 1000, 0.1);
    last = now;

    for (const fn of [...subscribers]) {
        fn(dt, now);
    }

    if (subscribers.size > 0) {
        requestAnimationFrame(frame);
    } else {
        running = false;
    }
}

/**
 * Subscribe a per-frame callback (dt in seconds). Returns an unsubscribe fn.
 */
export function onFrame(fn) {
    subscribers.add(fn);
    if (!running) {
        running = true;
        last = performance.now();
        requestAnimationFrame(frame);
    }
    return () => subscribers.delete(fn);
}

export const reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)');
