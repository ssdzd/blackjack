/**
 * Quant HUD: the side panel's instruments.
 *
 * Every number here is computed by the server's statistical engine
 * (core.statistics) and shipped in the WS state payload — running/true
 * count, player edge at the current count, half-Kelly stake, risk of
 * ruin, N0, dealer bust probability — plus a bankroll sparkline.
 */

import { attachCounter } from '../juice/counter.js';

let rcCounter = null;
let tcEl = null;
let sparkPoints = [];
let lastVisibility = 'always';

function fmtCount(value) {
    if (value === null || value === undefined) return '—';
    const rounded = Math.round(value * 10) / 10;
    return Number.isInteger(rounded) ? String(rounded) : rounded.toFixed(1);
}

function signed(value, digits = 1) {
    const v = Number(value);
    const s = v.toFixed(digits);
    return v > 0 ? `+${s}` : s;
}

export function initHud() {
    const rcSpan = document.querySelector('#running-count span');
    if (rcSpan) {
        rcCounter = attachCounter(rcSpan, {
            format: fmtCount,
            flashClass: 'counter-flash',
        });
    }
    tcEl = document.querySelector('#true-count span');
}

function setText(selector, text) {
    const el = document.querySelector(selector);
    if (el) el.textContent = text;
}

function drawSparkline() {
    const canvas = document.getElementById('bankroll-spark');
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    const w = canvas.width;
    const h = canvas.height;
    ctx.clearRect(0, 0, w, h);
    if (sparkPoints.length < 2) return;

    const points = sparkPoints.slice(-48);
    const min = Math.min(...points);
    const max = Math.max(...points);
    const range = max - min || 1;
    const pad = 4;

    // Baseline (starting bankroll of the visible window)
    const baseY = h - pad - ((points[0] - min) / range) * (h - 2 * pad);
    ctx.strokeStyle = 'rgba(243, 236, 221, 0.15)';
    ctx.setLineDash([3, 3]);
    ctx.beginPath();
    ctx.moveTo(pad, baseY);
    ctx.lineTo(w - pad, baseY);
    ctx.stroke();
    ctx.setLineDash([]);

    const up = points[points.length - 1] >= points[0];
    ctx.strokeStyle = up ? '#d4af37' : '#cf5f6d';
    ctx.lineWidth = 1.5;
    ctx.beginPath();
    points.forEach((p, i) => {
        const x = pad + (i / (points.length - 1)) * (w - 2 * pad);
        const y = h - pad - ((p - min) / range) * (h - 2 * pad);
        if (i === 0) ctx.moveTo(x, y);
        else ctx.lineTo(x, y);
    });
    ctx.stroke();

    // Endpoint dot
    const lastX = w - pad;
    const lastY = h - pad - ((points[points.length - 1] - min) / range) * (h - 2 * pad);
    ctx.fillStyle = up ? '#ecd489' : '#cf5f6d';
    ctx.beginPath();
    ctx.arc(lastX, lastY, 2.5, 0, Math.PI * 2);
    ctx.fill();
}

export function pushBankrollPoint(value) {
    sparkPoints.push(value);
    if (sparkPoints.length > 200) sparkPoints = sparkPoints.slice(-100);
    drawSparkline();
}

export function resetSparkline(value = null) {
    sparkPoints = value === null ? [] : [value];
    drawSparkline();
}

/** Apply count + quant data from a server state payload. */
export function updateHud(state) {
    const countSection = document.getElementById('count-section');
    const quantSection = document.getElementById('quant-section');
    const revealBtn = document.getElementById('btn-reveal-count');

    const visibility = state.visibility || 'always';
    if (visibility !== lastVisibility) {
        lastVisibility = visibility;
        countSection?.classList.toggle('count-hidden-mode', visibility === 'hidden');
        revealBtn?.classList.toggle('hidden', visibility !== 'on_request');
    }

    if (state.count) {
        applyCount(state.count);
    } else if (visibility === 'hidden') {
        if (rcCounter) rcCounter.set(0, { instant: true });
        setText('#running-count span', '?');
        setText('#true-count span', '?');
    }

    if (state.quant) {
        applyQuant(state.quant);
        quantSection?.classList.remove('hidden');
    } else if (visibility === 'hidden') {
        quantSection?.classList.add('hidden');
    }

    // Cards remaining is never secret (you can see the discard tray)
    if (state.shoe_cards_remaining !== undefined) {
        setText('#cards-remaining span', state.shoe_cards_remaining);
    }

    const houseEdge = state.rules?.house_edge_pct;
    if (houseEdge !== undefined) {
        setText('#hud-house-edge span', `${houseEdge.toFixed(2)}%`);
    }
}

/** Apply a count payload (from state or an explicit reveal). */
export function applyCount(count) {
    if (rcCounter) {
        rcCounter.set(count.running);
    } else {
        setText('#running-count span', fmtCount(count.running));
    }
    if (tcEl) {
        tcEl.textContent = count.balanced ? fmtCount(count.true) : '—';
        tcEl.title = count.balanced ? '' : `${count.system} is unbalanced: play from the running count`;
    }
    const sysEl = document.getElementById('hud-system');
    if (sysEl) sysEl.textContent = count.system.replace('_', ' ');
}

export function applyQuant(quant) {
    const edge = quant.player_edge_pct;
    const edgeEl = document.querySelector('#hud-edge span');
    if (edgeEl) {
        edgeEl.textContent = `${signed(edge, 2)}%`;
        edgeEl.className = edge > 0 ? 'quant-good' : (edge < -0.4 ? 'quant-bad' : '');
    }
    setText('#hud-kelly span', `$${quant.kelly_bet}`);
    setText('#hud-ror span', `${quant.risk_of_ruin_pct.toFixed(1)}%`);
    setText('#hud-n0 span', quant.n_zero ? quant.n_zero.toLocaleString() : '—');
    setText(
        '#hud-dealer-bust span',
        quant.dealer_bust_pct !== null && quant.dealer_bust_pct !== undefined
            ? `${quant.dealer_bust_pct.toFixed(0)}%`
            : '—'
    );
}
