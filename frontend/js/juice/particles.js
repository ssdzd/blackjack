/**
 * Pooled particle system on a single full-screen canvas overlay.
 *
 * Ported from pygame_ui/core/particles.py: gravity, drag, rotation, fade;
 * emitters for confetti / sparks / coins. Pool-capped so a celebration can
 * never tank the frame rate.
 */

import { onFrame, reducedMotion } from './loop.js';

// Measured (headless Chromium, CDP CPU throttling 1x/4x/6x): a realistic
// single burst (count=60, matching the venue-clear/daily-complete call
// sites) costs ~7-9% of frames >33ms during its ~1.7s lifetime, worst
// case ~50ms; median frame time stays at 16.7ms throughout. Stacking 5
// bursts back to back (300 particles, the POOL_MAX ceiling) pushes that
// to ~11%, essentially flat from 1x to 6x throttle -- the cost is
// canvas-fill/compositing-bound, not JS-bound, so it doesn't scale with
// CPU speed and lowering POOL_MAX wouldn't reduce a single burst's cost
// (that's set by count, not the pool ceiling). Idle rAF work (tweens,
// springs, HUD counters) shows zero jitter even at 6x throttle. Not
// worth tuning at current call-site counts (max real count is 60).
const POOL_MAX = 300;

const GOLD = ['#d4af37', '#ecd489', '#f5e7b8', '#96762a'];
const CONFETTI = ['#d4af37', '#ecd489', '#f3ecdd', '#ae2438', '#2c5a43'];

let canvas = null;
let ctx = null;
let particles = [];
let unsubscribe = null;

function ensureCanvas() {
    if (canvas) return true;
    canvas = document.getElementById('fx-canvas');
    if (!canvas) return false;
    ctx = canvas.getContext('2d');
    resize();
    window.addEventListener('resize', resize);
    return true;
}

function resize() {
    const dpr = Math.min(window.devicePixelRatio || 1, 2);
    canvas.width = Math.floor(window.innerWidth * dpr);
    canvas.height = Math.floor(window.innerHeight * dpr);
    canvas.style.width = window.innerWidth + 'px';
    canvas.style.height = window.innerHeight + 'px';
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
}

function spawn(p) {
    if (particles.length >= POOL_MAX) particles.shift();
    particles.push(p);
    if (!unsubscribe) unsubscribe = onFrame(step);
}

function step(dt) {
    ctx.clearRect(0, 0, window.innerWidth, window.innerHeight);

    particles = particles.filter(p => {
        p.life -= dt;
        if (p.life <= 0) return false;

        p.vx *= Math.pow(p.drag, dt * 60);
        p.vy = p.vy * Math.pow(p.drag, dt * 60) + p.gravity * dt;
        p.x += p.vx * dt;
        p.y += p.vy * dt;
        p.rot += p.vrot * dt;

        const alpha = Math.min(1, p.life / (p.maxLife * 0.4));
        ctx.save();
        ctx.globalAlpha = alpha;
        ctx.translate(p.x, p.y);
        ctx.rotate(p.rot);
        ctx.fillStyle = p.color;

        if (p.shape === 'rect') {
            ctx.fillRect(-p.size / 2, -p.size / 4, p.size, p.size / 2);
        } else {
            ctx.beginPath();
            ctx.arc(0, 0, p.size / 2, 0, Math.PI * 2);
            ctx.fill();
        }
        ctx.restore();
        return true;
    });

    if (particles.length === 0) {
        ctx.clearRect(0, 0, window.innerWidth, window.innerHeight);
        unsubscribe?.();
        unsubscribe = null;
    }
}

const rand = (lo, hi) => lo + Math.random() * (hi - lo);
const pick = arr => arr[Math.floor(Math.random() * arr.length)];

/** Gold-and-ivory confetti burst (blackjacks, badges). */
export function confettiBurst(x, y, { count = 44, colors = CONFETTI } = {}) {
    if (reducedMotion.matches || !ensureCanvas()) return;
    for (let i = 0; i < count; i++) {
        const angle = rand(0, Math.PI * 2);
        const speed = rand(140, 460);
        spawn({
            x, y,
            vx: Math.cos(angle) * speed,
            vy: Math.sin(angle) * speed - rand(120, 260),
            gravity: 780,
            drag: 0.985,
            rot: rand(0, Math.PI * 2),
            vrot: rand(-9, 9),
            size: rand(6, 12),
            color: pick(colors),
            shape: 'rect',
            life: rand(0.9, 1.7),
            maxLife: 1.7,
        });
    }
}

/** Quick gold sparks (good decisions, chips landing). */
export function sparkBurst(x, y, { count = 14 } = {}) {
    if (reducedMotion.matches || !ensureCanvas()) return;
    for (let i = 0; i < count; i++) {
        const angle = rand(0, Math.PI * 2);
        const speed = rand(60, 300);
        spawn({
            x, y,
            vx: Math.cos(angle) * speed,
            vy: Math.sin(angle) * speed,
            gravity: 150,
            drag: 0.9,
            rot: 0,
            vrot: 0,
            size: rand(2.5, 5),
            color: pick(GOLD),
            shape: 'dot',
            life: rand(0.25, 0.6),
            maxLife: 0.6,
        });
    }
}

/** Coin fountain for won money. */
export function coinFountain(x, y, { count = 20 } = {}) {
    if (reducedMotion.matches || !ensureCanvas()) return;
    for (let i = 0; i < count; i++) {
        spawn({
            x: x + rand(-24, 24), y,
            vx: rand(-130, 130),
            vy: rand(-560, -260),
            gravity: 1050,
            drag: 0.995,
            rot: rand(0, Math.PI),
            vrot: rand(-6, 6),
            size: rand(6, 10),
            color: pick(GOLD),
            shape: 'dot',
            life: rand(0.8, 1.4),
            maxLife: 1.4,
        });
    }
}

/** Burst centered on a DOM element. */
export function burstAt(el, kind = 'confetti', opts = {}) {
    if (!el) return;
    const rect = el.getBoundingClientRect();
    const x = rect.left + rect.width / 2;
    const y = rect.top + rect.height / 2;
    if (kind === 'confetti') confettiBurst(x, y, opts);
    else if (kind === 'sparks') sparkBurst(x, y, opts);
    else if (kind === 'coins') coinFountain(x, y, opts);
}
