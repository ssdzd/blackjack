/**
 * The play screen: game flow over WebSocket, choreographed playback,
 * controls, and in-play hints.
 *
 * WS events arrive in a burst (the server resolves a whole dealer turn
 * instantly). Each event carries a full state snapshot, so playback
 * enqueues them and applies snapshots on timed beats — cards land one by
 * one, the hole card flips, the result crunches — while any user input
 * flushes the queue instantly to keep the UI honest.
 */

import { BlackjackClient } from '../ws.js';
import { getSessionId } from '../api.js';
import { appState } from '../state.js';
import { StatsTracker } from '../session-stats.js';
import { getHandInfo } from '../hand-info.js';
import { getBestPlay, getActionClass, ACTION_NAMES } from '../strategy-data.js';
import { refreshChartHighlight } from './strategy-chart.js';
import { syncTable, initCardTilt } from '../components/cards3d.js';
import { initHud, updateHud, applyCount, applyQuant, pushBankrollPoint, resetSparkline } from '../components/hud.js';
import { handleProgressionDelta } from '../progression.js';
import { wait } from '../juice/tween.js';
import { addShake, SHAKE } from '../juice/shake.js';
import { burstAt, sparkBurst } from '../juice/particles.js';
import { play } from '../juice/sound.js';
import { toast } from '../juice/toast.js';
import { attachCounter } from '../juice/counter.js';

let wsClient = null;
export let statsTracker = null;

let lastBetAmount = 10;
// The engine auto-advances to WAITING_FOR_BET after resolving a round, so
// this flag keeps the result panel up until the player starts the next round.
let showingResult = false;
let bestPlayHintEnabled = true;
let betHintsEnabled = true;
let bankrollCounter = null;

// ---- Event choreography queue ----

const queue = [];
let draining = false;
let flushing = false;

function enqueue(item) {
    queue.push(item);
    if (!draining) drain();
}

async function drain() {
    draining = true;
    while (queue.length) {
        const item = queue.shift();
        try {
            await playbackStep(item);
        } catch (err) {
            console.error('Playback error:', err);
        }
    }
    draining = false;
    flushing = false;
}

/** Apply all pending steps instantly (called before any user action). */
function flushQueue() {
    flushing = true;
}

function beat(ms) {
    return flushing ? Promise.resolve() : wait(ms);
}

async function playbackStep(item) {
    if (item.kind === 'state') {
        applyState(item.state);
        return;
    }

    if (item.kind === 'grade') {
        showDecisionFeedback(item.grade);
        return;
    }

    if (item.kind === 'progression') {
        handleProgressionDelta(item.delta);
        return;
    }

    const { event_type, state } = item.data;
    const data = item.data.data || {};

    switch (event_type) {
        case 'CARD_DEALT':
            applyState(state);
            play('deal');
            await beat(120);
            break;

        case 'DEALER_REVEALS':
            applyState(state);
            play('flip');
            await beat(400);
            break;

        case 'DEALER_HITS':
            applyState(state);
            await beat(60);
            break;

        case 'BET_PLACED':
            applyState(state);
            play('chip');
            break;

        case 'SHOE_SHUFFLED':
            play('shuffle');
            toast('Shoe shuffled — the count resets', { variant: 'gold' });
            applyState(state);
            break;

        case 'PLAYER_BUSTS':
            applyState(state);
            play('bust');
            addShake(SHAKE.LIGHT);
            await beat(280);
            break;

        case 'PLAYER_BLACKJACK':
            applyState(state);
            showMessage('Blackjack!');
            play('blackjack');
            addShake(SHAKE.MEDIUM);
            burstAt(document.getElementById('player-hands'), 'confetti');
            await beat(480);
            break;

        case 'DEALER_BLACKJACK':
            applyState(state);
            showMessage('Dealer Blackjack');
            await beat(240);
            break;

        case 'DEALER_BUSTS':
            applyState(state);
            burstAt(document.getElementById('dealer-cards'), 'sparks');
            await beat(200);
            break;

        case 'ROUND_ENDED': {
            const result = data.result || 0;
            const outcome = result > 0 ? 'win' : (result < 0 ? 'lose' : 'push');
            statsTracker.recordHand({
                outcome: outcome,
                amount: Math.abs(result),
                wager: lastBetAmount,
            });
            showingResult = true;
            showRoundResult(result);
            applyState(state);

            if (result > 0) {
                play('win');
                addShake(SHAKE.LIGHT);
                burstAt(document.getElementById('player-hands'), 'coins');
            } else if (result < 0) {
                play('lose');
                pulseFelt();
            } else {
                play('push');
            }
            if (state?.bankroll !== undefined) {
                pushBankrollPoint(state.bankroll);
            }
            await beat(320);
            break;
        }

        default:
            applyState(state);
            break;
    }
}

function pulseFelt() {
    const felt = document.getElementById('table-felt');
    if (!felt) return;
    felt.classList.remove('pulse-loss');
    void felt.offsetWidth;
    felt.classList.add('pulse-loss');
}

/** Show the server's grade for the last decision (the education beat). */
function showDecisionFeedback(grade) {
    if (!grade || grade.kind === 'bet') {
        // Bet sizing feedback lives in the betting hint, not a chip
        return;
    }

    const el = document.getElementById('decision-feedback');
    if (!el) return;

    const action = (grade.action || '').toUpperCase();
    const correct = (grade.correct_action || '').toUpperCase();

    let headline;
    let detail = '';
    if (grade.is_correct) {
        headline = grade.is_deviation ? `✓ ${action} — index play` : `✓ ${action}`;
        if (grade.is_deviation && grade.deviation) {
            detail = grade.deviation.description;
        }
        sparkBurst(el.getBoundingClientRect().left + 40, el.getBoundingClientRect().top + 10, { count: 8 });
    } else {
        headline = `✗ ${action} — book says ${correct}`;
        const parts = [];
        if (grade.deviation) {
            parts.push(grade.deviation.description);
        } else if (grade.why?.dealer_bust_pct !== undefined) {
            parts.push(`${grade.why.hand}: dealer busts ${grade.why.dealer_bust_pct}% of the time`);
        }
        if (typeof grade.why?.ev_cost_pct === 'number' && grade.why.ev_cost_pct > 0) {
            parts.push(`cost you ~${grade.why.ev_cost_pct.toFixed(1)}% EV`);
        }
        detail = parts.join(' · ');
    }

    el.querySelector('.feedback-headline').textContent = headline;
    el.querySelector('.feedback-detail').textContent = detail;
    el.className = grade.is_correct ? 'feedback-correct' : 'feedback-wrong';
    el.classList.remove('hidden');
    el.classList.add('feedback-pop');

    clearTimeout(el._hideTimer);
    el._hideTimer = setTimeout(() => {
        el.classList.add('hidden');
        el.classList.remove('feedback-pop');
    }, grade.is_correct ? 2200 : 4200);
}

// ---- Init / transport ----

export function initTable() {
    statsTracker = new StatsTracker();

    const bankrollEl = document.getElementById('bankroll-amount');
    if (bankrollEl) {
        bankrollCounter = attachCounter(bankrollEl, { flashClass: 'counter-flash' });
    }

    initHud();
    connectWebSocket();
    wireControls();
    wireKeyboard();
    initCardTilt();
}

/** Send a configure message (settings screen, career mode). */
export function configureSession(options) {
    if (!wsClient) return;
    flushQueue();
    wsClient.send('configure', options);
}

function connectWebSocket() {
    wsClient = new BlackjackClient();

    wsClient.on('connected', () => {
        console.log('Connected to game server');
        document.getElementById('connection-status')?.classList.add('connected');
    });

    wsClient.on('disconnected', () => {
        console.log('Disconnected from game server');
        document.getElementById('connection-status')?.classList.remove('connected');
    });

    wsClient.on('state_update', (data) => {
        enqueue({ kind: 'state', state: data.state });
    });

    wsClient.on('event', (data) => {
        enqueue({ kind: 'event', data });
    });

    wsClient.on('decision_result', (data) => {
        enqueue({ kind: 'grade', grade: data.grade });
    });

    wsClient.on('progression', (data) => {
        enqueue({ kind: 'progression', delta: data.delta });
    });

    for (const type of ['daily_started', 'daily_progress', 'count_checkin_request', 'count_checkin_result', 'daily_complete']) {
        wsClient.on(type, (data) => {
            dailyListeners.forEach(fn => fn(type, data));
        });
    }

    for (const type of ['venue_entered', 'heat', 'backed_off', 'venue_complete', 'venue_bust', 'trap_walkaway', 'venue_left']) {
        wsClient.on(type, (data) => {
            venueListeners.forEach(fn => fn(type, data));
        });
    }

    wsClient.on('count_reveal', (data) => {
        applyCount(data.count);
        if (data.quant) applyQuant(data.quant);
        toast(`Running ${data.count.running >= 0 ? '+' : ''}${data.count.running}`, {
            variant: 'gold',
            title: 'Count revealed',
        });
    });

    wsClient.on('error', (data) => {
        showError(data.message);
    });

    wsClient.connect(getSessionId());
}

/** One-shot count reveal (on_request visibility mode). */
export function revealCount() {
    wsClient?.send('reveal_count');
}

// ---- Daily challenge plumbing ----

const dailyListeners = [];

/** Subscribe to daily-challenge messages (started/progress/checkin/complete). */
export function onDaily(fn) {
    dailyListeners.push(fn);
}

export function startDailyRun() {
    showingResult = false;
    flushQueue();
    wsClient?.send('start_daily');
}

export function sendCountCheckin(runningCount) {
    wsClient?.send('count_checkin', { running_count: runningCount });
}

// ---- Career plumbing ----

const venueListeners = [];

export function onVenue(fn) {
    venueListeners.push(fn);
}

export function enterVenue(venueId) {
    showingResult = false;
    flushQueue();
    wsClient?.send('configure', { venue_id: venueId });
}

export function leaveVenue() {
    showingResult = false;
    flushQueue();
    wsClient?.send('leave_venue');
}

// ---- State application (single source of DOM truth) ----

export function renderGameState(state) {
    enqueue({ kind: 'state', state });
}

function applyState(state) {
    if (!state) return;
    appState.gameState = state;

    if (bankrollCounter) {
        bankrollCounter.set(state.bankroll);
    }

    updateHud(state);
    syncTable(state);

    // Dealer value line
    const dealerValue = document.getElementById('dealer-value');
    if (state.state === 'PLAYER_TURN') {
        dealerValue.textContent = state.dealer_showing ? `Showing: ${state.dealer_showing}` : '';
    } else if (state.dealer_hand.value) {
        dealerValue.textContent = state.dealer_hand.value;
    } else {
        dealerValue.textContent = '';
    }

    updateControls(state);

    updateBestPlayTooltip(state);
    updateBettingHint(state);
    refreshChartHighlight();
}

/** True count from the server payload (0 when hidden/unbalanced). */
function serverTrueCount(state) {
    const tc = state?.count?.true;
    return typeof tc === 'number' ? tc : 0;
}

function updateControls(state) {
    const bettingControls = document.getElementById('betting-controls');
    const actionControls = document.getElementById('action-controls');
    const resultControls = document.getElementById('result-controls');
    const insuranceControls = document.getElementById('insurance-controls');

    // Hide all first
    bettingControls.classList.add('hidden');
    actionControls.classList.add('hidden');
    resultControls.classList.add('hidden');
    insuranceControls?.classList.add('hidden');

    switch (state.state) {
        case 'WAITING_FOR_BET':
            if (showingResult) {
                // Round just resolved; keep the result up until "New Round"
                resultControls.classList.remove('hidden');
            } else {
                bettingControls.classList.remove('hidden');
                // Clear any previous result
                document.getElementById('round-result').textContent = '';
                document.getElementById('round-result').className = '';
            }
            break;

        case 'OFFERING_INSURANCE':
            insuranceControls?.classList.remove('hidden');
            document.getElementById('btn-take-insurance').disabled = !state.can_insure;
            updateInsuranceHint();
            break;

        case 'PLAYER_TURN':
            actionControls.classList.remove('hidden');
            document.getElementById('btn-hit').disabled = !state.can_hit;
            document.getElementById('btn-stand').disabled = !state.can_stand;
            document.getElementById('btn-double').disabled = !state.can_double;
            document.getElementById('btn-split').disabled = !state.can_split;
            document.getElementById('btn-surrender').disabled = !state.can_surrender;
            break;

        case 'ROUND_COMPLETE':
        case 'GAME_OVER':
            resultControls.classList.remove('hidden');
            break;

        case 'DEALING':
        case 'DEALER_TURN':
        case 'RESOLVING':
            // Show nothing - game is processing
            break;
    }
}

function showRoundResult(result) {
    const resultEl = document.getElementById('round-result');

    if (result > 0) {
        resultEl.textContent = `Won $${result.toFixed(0)}!`;
        resultEl.className = 'win';
    } else if (result < 0) {
        resultEl.textContent = `Lost $${Math.abs(result).toFixed(0)}`;
        resultEl.className = 'lose';
    } else {
        resultEl.textContent = 'Push';
        resultEl.className = 'push';
    }
}

export function showMessage(message) {
    const msgEl = document.getElementById('game-message');
    if (msgEl) {
        msgEl.textContent = message;
        msgEl.classList.add('visible');
        setTimeout(() => msgEl.classList.remove('visible'), 2000);
    }
}

export function showError(message) {
    console.error('Game error:', message);
    const msgEl = document.getElementById('game-message');
    if (msgEl) {
        msgEl.textContent = message;
        msgEl.classList.add('visible', 'error');
        setTimeout(() => msgEl.classList.remove('visible', 'error'), 3000);
    }
}

// ---- Actions ----

function placeBet() {
    const amount = parseInt(document.getElementById('bet-amount').value);
    if (amount < 10 || amount > 1000) {
        showError('Bet must be between $10 and $1000');
        return;
    }
    lastBetAmount = amount;
    flushQueue();
    play('chip');
    wsClient.placeBet(amount);
}

function playerAction(action) {
    flushQueue();
    play('click');
    wsClient.action(action);
}

function newRound() {
    showingResult = false;
    document.getElementById('round-result').textContent = '';
    document.getElementById('round-result').className = '';
    flushQueue();
    wsClient.newRound();
}

export function resetGame() {
    showingResult = false;
    statsTracker.reset();
    resetSparkline();
    flushQueue();
    wsClient.send('reset_game');
}

function takeInsurance() {
    flushQueue();
    play('chip');
    wsClient.send('insurance', { take: true });
}

function declineInsurance() {
    flushQueue();
    play('click');
    wsClient.send('insurance', { take: false });
}

// ---- Hints ----

function updateInsuranceHint() {
    const hintEl = document.getElementById('insurance-hint');
    if (!hintEl) return;

    if (!betHintsEnabled) {
        hintEl.classList.add('hidden');
        return;
    }

    const trueCount = serverTrueCount(appState.gameState);
    const hintAction = hintEl.querySelector('.hint-action');

    // Insurance is profitable at TC +3 or higher
    if (trueCount >= 3) {
        hintAction.textContent = 'TAKE (TC +3+)';
        hintAction.className = 'hint-action take-insurance';
    } else {
        hintAction.textContent = 'DECLINE (TC < +3)';
        hintAction.className = 'hint-action decline-insurance';
    }

    hintEl.classList.remove('hidden');
}

function updateBestPlayTooltip(state) {
    const tooltip = document.getElementById('best-play-tooltip');
    if (!tooltip) return;

    if (!bestPlayHintEnabled || state?.state !== 'PLAYER_TURN') {
        tooltip.classList.add('hidden');
        return;
    }

    const handInfo = getHandInfo(state);
    if (!handInfo) {
        tooltip.classList.add('hidden');
        return;
    }

    const trueCount = serverTrueCount(state);
    const bestPlay = getBestPlay(handInfo, trueCount);

    const actionEl = tooltip.querySelector('.tooltip-action');
    const reasonEl = tooltip.querySelector('.tooltip-reason');
    const devBadge = tooltip.querySelector('.tooltip-deviation');

    actionEl.textContent = ACTION_NAMES[bestPlay.action] || bestPlay.action;
    actionEl.className = `tooltip-action action-${getActionClass(bestPlay.action).replace('action-', '')}`;

    reasonEl.textContent = bestPlay.reason;

    if (bestPlay.isDeviation) {
        devBadge.classList.remove('hidden');
        tooltip.classList.add('has-deviation');
    } else {
        devBadge.classList.add('hidden');
        tooltip.classList.remove('has-deviation');
    }

    tooltip.classList.remove('hidden');
}

function updateBettingHint(state) {
    const hintEl = document.getElementById('betting-hint');
    if (!hintEl) return;

    // The hint needs the server's quant data (real Kelly math); without it
    // (hidden visibility) there is nothing honest to show.
    if (!betHintsEnabled || state?.state !== 'WAITING_FOR_BET' || !state?.quant) {
        hintEl.classList.add('hidden');
        return;
    }

    const quant = state.quant;
    const edge = quant.player_edge_pct;
    const trueCount = serverTrueCount(state);

    let level;
    if (edge < -0.2) level = 'negative';
    else if (edge < 0.2) level = 'breakeven';
    else if (edge < 1.0) level = 'positive';
    else level = 'strong';

    const message = edge > 0
        ? `Bet $${quant.kelly_bet} — half-Kelly for this edge`
        : `Table minimum — the house has the edge`;

    hintEl.querySelector('.hint-units').textContent = message;
    hintEl.querySelector('.hint-edge').textContent = `Your edge: ${edge >= 0 ? '+' : ''}${edge.toFixed(2)}%`;
    hintEl.querySelector('.hint-count span').textContent =
        state.count?.balanced ? trueCount.toFixed(1) : 'RC ' + (state.count?.running ?? '—');

    hintEl.className = '';
    hintEl.classList.add(`advantage-${level}`);

    hintEl.classList.remove('hidden');
}

// ---- Wiring ----

function wireControls() {
    document.getElementById('btn-bet')?.addEventListener('click', placeBet);
    document.getElementById('btn-hit')?.addEventListener('click', () => playerAction('hit'));
    document.getElementById('btn-stand')?.addEventListener('click', () => playerAction('stand'));
    document.getElementById('btn-double')?.addEventListener('click', () => playerAction('double'));
    document.getElementById('btn-split')?.addEventListener('click', () => playerAction('split'));
    document.getElementById('btn-surrender')?.addEventListener('click', () => playerAction('surrender'));
    document.getElementById('btn-new-round')?.addEventListener('click', newRound);
    document.getElementById('btn-take-insurance')?.addEventListener('click', takeInsurance);
    document.getElementById('btn-decline-insurance')?.addEventListener('click', declineInsurance);

    document.getElementById('toggle-best-play')?.addEventListener('change', (e) => {
        bestPlayHintEnabled = e.target.checked;
        if (appState.gameState) updateBestPlayTooltip(appState.gameState);
    });

    document.getElementById('toggle-bet-hints')?.addEventListener('change', (e) => {
        betHintsEnabled = e.target.checked;
        if (appState.gameState) updateBettingHint(appState.gameState);
    });
}

function wireKeyboard() {
    document.addEventListener('keydown', (e) => {
        if (appState.mode !== 'play') return;
        if (document.activeElement.tagName === 'INPUT') return;

        // Don't process if the strategy chart modal is open
        if (!document.getElementById('strategy-chart-modal')?.classList.contains('hidden')) return;

        switch (e.key.toLowerCase()) {
            case 'h':
                if (!document.getElementById('btn-hit').disabled) playerAction('hit');
                break;
            case 's':
                if (!document.getElementById('btn-stand').disabled) playerAction('stand');
                break;
            case 'd':
                if (!document.getElementById('btn-double').disabled) playerAction('double');
                break;
            case 'p':
                if (!document.getElementById('btn-split').disabled) playerAction('split');
                break;
            case 'r':
                if (!document.getElementById('btn-surrender').disabled) playerAction('surrender');
                break;
            case 'b':
                if (!document.getElementById('betting-controls').classList.contains('hidden')) placeBet();
                break;
            case 'n':
                // N = New round OR No insurance depending on state
                if (!document.getElementById('result-controls').classList.contains('hidden')) {
                    newRound();
                } else if (!document.getElementById('insurance-controls')?.classList.contains('hidden')) {
                    declineInsurance();
                }
                break;
            case 'i':
                if (!document.getElementById('insurance-controls')?.classList.contains('hidden')) {
                    if (!document.getElementById('btn-take-insurance').disabled) takeInsurance();
                }
                break;
        }
    });
}
