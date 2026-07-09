/**
 * The play screen: game flow over WebSocket, controls, and in-play hints
 */

import { BlackjackClient } from '../ws.js';
import { getSessionId } from '../api.js';
import { appState } from '../state.js';
import { StatsTracker } from '../session-stats.js';
import { CountTracker } from '../count-local.js';
import { renderCard, renderHand } from '../components/cards.js';
import { getHandInfo } from '../hand-info.js';
import { getBestPlay, getBettingHint, getActionClass, ACTION_NAMES } from '../strategy-data.js';
import { refreshChartHighlight } from './strategy-chart.js';

let wsClient = null;
export let statsTracker = null;
export let countTracker = null;

let lastBetAmount = 10;
// The engine auto-advances to WAITING_FOR_BET after resolving a round, so
// this flag keeps the result panel up until the player starts the next round.
let showingResult = false;
let bestPlayHintEnabled = true;
let betHintsEnabled = true;

export function initTable() {
    statsTracker = new StatsTracker();
    countTracker = new CountTracker('hilo');

    connectWebSocket();
    wireControls();
    wireKeyboard();
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
        renderGameState(data.state);
    });

    wsClient.on('event', (data) => {
        handleGameEvent(data);
    });

    wsClient.on('error', (data) => {
        showError(data.message);
    });

    wsClient.connect(getSessionId());
}

function handleGameEvent(data) {
    const { event_type, state } = data;

    // Track cards for count
    if (event_type === 'CARD_DEALT' && data.data.card !== '??') {
        const card = data.data.card;
        // Extract rank from card string (e.g., "A♠" -> "A", "10♥" -> "10")
        const rank = card.replace(/[♠♥♦♣]/g, '');
        countTracker.countCard(rank);
    }

    // Reset count on shoe shuffle
    if (event_type === 'SHOE_SHUFFLED') {
        countTracker.reset(6);
        showMessage('Shoe shuffled!');
    }

    // Track round results
    if (event_type === 'ROUND_ENDED') {
        const result = data.data.result || 0;
        const outcome = result > 0 ? 'win' : (result < 0 ? 'lose' : 'push');
        statsTracker.recordHand({
            outcome: outcome,
            amount: Math.abs(result),
            wager: lastBetAmount,
        });
        showingResult = true;
        showRoundResult(result);
    }

    if (event_type === 'PLAYER_BLACKJACK') {
        showMessage('Blackjack!');
    }

    if (event_type === 'DEALER_BLACKJACK') {
        showMessage('Dealer Blackjack');
    }

    renderGameState(state);
}

export function renderGameState(state) {
    if (!state) return;
    appState.gameState = state;

    // Update bankroll
    document.getElementById('bankroll-amount').textContent = state.bankroll.toFixed(0);

    // Render dealer cards
    const dealerCards = document.getElementById('dealer-cards');
    dealerCards.innerHTML = state.dealer_hand.cards
        .map(card => renderCard(card))
        .join('');

    // Render dealer value
    const dealerValue = document.getElementById('dealer-value');
    if (state.state === 'PLAYER_TURN') {
        dealerValue.textContent = state.dealer_showing ? `Showing: ${state.dealer_showing}` : '';
    } else if (state.dealer_hand.value) {
        dealerValue.textContent = state.dealer_hand.value;
    } else {
        dealerValue.textContent = '';
    }

    // Render player hands
    const playerHands = document.getElementById('player-hands');
    if (state.player_hands && state.player_hands.length > 0) {
        playerHands.innerHTML = state.player_hands
            .map((hand, i) => renderHand(hand, i, i === state.current_hand_index && state.state === 'PLAYER_TURN'))
            .join('');
    } else {
        playerHands.innerHTML = '<div class="hand"><div class="cards"></div><div class="hand-value"></div></div>';
    }

    updateControls(state);

    // Update shoe info for count display
    if (state.shoe_cards_remaining) {
        const cardsEl = document.querySelector('#cards-remaining span');
        if (cardsEl) cardsEl.textContent = state.shoe_cards_remaining;
        countTracker.decksRemaining = state.shoe_decks_remaining;
        countTracker.updateDisplay();
    }

    // Update hints and the reference chart highlight
    updateBestPlayTooltip(state);
    updateBettingHint(state);
    refreshChartHighlight();
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

// --- Actions ---

function placeBet() {
    const amount = parseInt(document.getElementById('bet-amount').value);
    if (amount < 10 || amount > 1000) {
        showError('Bet must be between $10 and $1000');
        return;
    }
    lastBetAmount = amount;
    wsClient.placeBet(amount);
}

function playerAction(action) {
    wsClient.action(action);
}

function newRound() {
    showingResult = false;
    document.getElementById('round-result').textContent = '';
    document.getElementById('round-result').className = '';
    wsClient.newRound();
}

export function resetGame() {
    showingResult = false;
    statsTracker.reset();
    countTracker.reset(6);
    wsClient.send('reset_game');
}

function takeInsurance() {
    wsClient.send('insurance', { take: true });
}

function declineInsurance() {
    wsClient.send('insurance', { take: false });
}

// --- Hints ---

function updateInsuranceHint() {
    const hintEl = document.getElementById('insurance-hint');
    if (!hintEl) return;

    if (!betHintsEnabled) {
        hintEl.classList.add('hidden');
        return;
    }

    const trueCount = countTracker ? countTracker.trueCount : 0;
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

    const trueCount = countTracker ? countTracker.trueCount : 0;
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

    if (!betHintsEnabled || state?.state !== 'WAITING_FOR_BET') {
        hintEl.classList.add('hidden');
        return;
    }

    const trueCount = countTracker ? countTracker.trueCount : 0;
    const hint = getBettingHint(trueCount);

    hintEl.querySelector('.hint-units').textContent = hint.message;
    hintEl.querySelector('.hint-edge').textContent = `Player edge: ${hint.edge >= 0 ? '+' : ''}${hint.edge.toFixed(1)}%`;
    hintEl.querySelector('.hint-count span').textContent = trueCount.toFixed(1);

    hintEl.className = '';
    hintEl.classList.add(`advantage-${hint.level}`);

    hintEl.classList.remove('hidden');
}

// --- Wiring ---

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
