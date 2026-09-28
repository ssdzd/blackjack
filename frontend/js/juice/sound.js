/**
 * Procedural WebAudio sound effects.
 *
 * Ported from pygame_ui/core/sound_generator.py — oscillators and noise
 * buffers shaped by gain envelopes, no audio files. The AudioContext is
 * created lazily on the first user gesture (autoplay policy) and every
 * play call is a no-op until then.
 */

let ctx = null;
let master = null;
let noiseBuffer = null;
let muted = localStorage.getItem('bjt-muted') === '1';

function ensureContext() {
    if (ctx) return true;
    const AC = window.AudioContext || window.webkitAudioContext;
    if (!AC) return false;
    ctx = new AC();
    master = ctx.createGain();
    master.gain.value = 0.4;
    master.connect(ctx.destination);

    // 1s of white noise, reused by every noise-based effect
    const len = ctx.sampleRate;
    noiseBuffer = ctx.createBuffer(1, len, ctx.sampleRate);
    const data = noiseBuffer.getChannelData(0);
    for (let i = 0; i < len; i++) data[i] = Math.random() * 2 - 1;
    return true;
}

/** Call once from main: arms context creation on the first gesture. */
export function armSound() {
    const arm = () => {
        if (ensureContext() && ctx.state === 'suspended') ctx.resume();
        document.removeEventListener('pointerdown', arm);
        document.removeEventListener('keydown', arm);
    };
    document.addEventListener('pointerdown', arm);
    document.addEventListener('keydown', arm);
}

export function isMuted() {
    return muted;
}

export function setMuted(value) {
    muted = value;
    localStorage.setItem('bjt-muted', value ? '1' : '0');
}

function envGain(t0, attack, decay, peak = 1) {
    const g = ctx.createGain();
    g.gain.setValueAtTime(0.0001, t0);
    g.gain.exponentialRampToValueAtTime(Math.max(peak, 0.0001), t0 + attack);
    g.gain.exponentialRampToValueAtTime(0.0001, t0 + attack + decay);
    g.connect(master);
    return g;
}

function tone(freq, { type = 'sine', attack = 0.005, decay = 0.12, peak = 0.5, delay = 0, slideTo = null } = {}) {
    const t0 = ctx.currentTime + delay;
    const osc = ctx.createOscillator();
    osc.type = type;
    osc.frequency.setValueAtTime(freq, t0);
    if (slideTo) osc.frequency.exponentialRampToValueAtTime(slideTo, t0 + attack + decay);
    osc.connect(envGain(t0, attack, decay, peak));
    osc.start(t0);
    osc.stop(t0 + attack + decay + 0.05);
}

function noise({ attack = 0.003, decay = 0.09, peak = 0.35, delay = 0, filterFrom = 4000, filterTo = null } = {}) {
    const t0 = ctx.currentTime + delay;
    const src = ctx.createBufferSource();
    src.buffer = noiseBuffer;
    const filter = ctx.createBiquadFilter();
    filter.type = 'lowpass';
    filter.frequency.setValueAtTime(filterFrom, t0);
    if (filterTo) filter.frequency.exponentialRampToValueAtTime(filterTo, t0 + attack + decay);
    src.connect(filter);
    filter.connect(envGain(t0, attack, decay, peak));
    src.start(t0);
    src.stop(t0 + attack + decay + 0.05);
}

const SOUNDS = {
    deal: () => noise({ decay: 0.07, peak: 0.3, filterFrom: 5200, filterTo: 900 }),
    flip: () => {
        noise({ decay: 0.05, peak: 0.22, filterFrom: 3600, filterTo: 1400 });
        tone(720, { type: 'triangle', decay: 0.07, peak: 0.16 });
    },
    chip: () => {
        tone(1900, { decay: 0.035, peak: 0.22 });
        tone(2450, { decay: 0.03, peak: 0.16, delay: 0.035 });
    },
    click: () => tone(1050, { type: 'triangle', decay: 0.025, peak: 0.14 }),
    win: () => {
        tone(523.25, { decay: 0.14, peak: 0.32 });
        tone(659.25, { decay: 0.14, peak: 0.32, delay: 0.09 });
        tone(783.99, { decay: 0.22, peak: 0.34, delay: 0.18 });
    },
    blackjack: () => {
        tone(523.25, { decay: 0.13, peak: 0.32 });
        tone(659.25, { decay: 0.13, peak: 0.32, delay: 0.08 });
        tone(783.99, { decay: 0.13, peak: 0.32, delay: 0.16 });
        tone(1046.5, { decay: 0.34, peak: 0.36, delay: 0.24 });
    },
    lose: () => tone(150, { type: 'sine', decay: 0.28, peak: 0.3, slideTo: 78 }),
    bust: () => tone(220, { type: 'square', decay: 0.24, peak: 0.2, slideTo: 108 }),
    push: () => tone(440, { type: 'triangle', decay: 0.1, peak: 0.18 }),
    shuffle: () => {
        noise({ decay: 0.3, peak: 0.24, filterFrom: 2600, filterTo: 500 });
        noise({ decay: 0.2, peak: 0.18, delay: 0.16, filterFrom: 3200, filterTo: 700 });
    },
    badge: () => {
        tone(659.25, { decay: 0.12, peak: 0.3 });
        tone(987.77, { decay: 0.3, peak: 0.32, delay: 0.1 });
    },
};

export function play(name) {
    if (muted || !ctx || ctx.state !== 'running') return;
    SOUNDS[name]?.();
}
