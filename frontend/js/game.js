/**
 * Blackjack game UI logic with WebSocket real-time updates
 */

// Session state
let sessionId = localStorage.getItem('sessionId');
let wsClient = null;
let statsTracker = null;
let countTracker = null;
let countVisible = true;
let currentMode = 'play'; // 'play', 'count-drill', 'strategy-drill'
let lastBetAmount = 10;

// Initialize game
async function initGame() {
    // Generate session ID if needed
    if (!sessionId) {
        sessionId = generateSessionId();
        localStorage.setItem('sessionId', sessionId);
    }

    // Initialize trackers
    statsTracker = new StatsTracker();
    countTracker = new CountTracker('hilo');

    // Connect WebSocket
    connectWebSocket();

    // Setup navigation
    setupNavigation();

    // Setup count toggle
    setupCountToggle();
}

function generateSessionId() {
    return 'sess_' + Math.random().toString(36).substring(2, 15);
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

    wsClient.connect(sessionId);
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
        showRoundResult(result);
    }

    // Show blackjack
    if (event_type === 'PLAYER_BLACKJACK') {
        showMessage('Blackjack!');
    }

    // Show dealer blackjack
    if (event_type === 'DEALER_BLACKJACK') {
        showMessage('Dealer Blackjack');
    }

    // Update UI
    renderGameState(state);
}

function renderGameState(state) {
    if (!state) return;

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

    // Update controls visibility
    updateControls(state);

    // Update shoe info for count display
    if (state.shoe_cards_remaining) {
        const cardsEl = document.querySelector('#cards-remaining span');
        if (cardsEl) cardsEl.textContent = state.shoe_cards_remaining;
        countTracker.decksRemaining = state.shoe_decks_remaining;
        countTracker.updateDisplay();
    }
}

function renderCard(card) {
    if (card.hidden || card.rank === '?') {
        return '<div class="card face-down"><span>?</span></div>';
    }

    const suit = getSuitSymbol(card.suit);
    const isRed = suit === '♥' || suit === '♦';
    const displayRank = formatRank(card.rank);

    return `<div class="card ${isRed ? 'red' : ''}">
        <span class="card-rank">${displayRank}</span>
        <span class="card-suit">${suit}</span>
    </div>`;
}

function formatRank(rank) {
    const rankMap = {
        'ACE': 'A', 'KING': 'K', 'QUEEN': 'Q', 'JACK': 'J',
        'TEN': '10', 'NINE': '9', 'EIGHT': '8', 'SEVEN': '7',
        'SIX': '6', 'FIVE': '5', 'FOUR': '4', 'THREE': '3', 'TWO': '2'
    };
    return rankMap[rank] || rank;
}

function getSuitSymbol(suit) {
    const symbols = {
        'CLUBS': '♣', 'DIAMONDS': '♦', 'HEARTS': '♥', 'SPADES': '♠',
        '♣': '♣', '♦': '♦', '♥': '♥', '♠': '♠'
    };
    return symbols[suit] || suit;
}

function renderHand(hand, index, isActive) {
    const activeClass = isActive ? 'active' : '';
    let statusText = '';

    if (hand.is_blackjack) {
        statusText = 'BLACKJACK!';
    } else if (hand.is_busted) {
        statusText = 'BUST';
    } else {
        statusText = (hand.is_soft ? 'Soft ' : '') + hand.value;
    }

    return `
        <div class="hand ${activeClass}" id="hand-${index}">
            <div class="cards">
                ${hand.cards.map(card => renderCard(card)).join('')}
            </div>
            <div class="hand-value">
                ${statusText}
                ${hand.bet ? ` <span class="bet-amount">$${hand.bet}</span>` : ''}
            </div>
        </div>
    `;
}

function updateControls(state) {
    const bettingControls = document.getElementById('betting-controls');
    const actionControls = document.getElementById('action-controls');
    const resultControls = document.getElementById('result-controls');

    // Hide all first
    bettingControls.classList.add('hidden');
    actionControls.classList.add('hidden');
    resultControls.classList.add('hidden');

    switch (state.state) {
        case 'WAITING_FOR_BET':
            bettingControls.classList.remove('hidden');
            // Clear any previous result
            document.getElementById('round-result').textContent = '';
            document.getElementById('round-result').className = '';
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

function showMessage(message) {
    const msgEl = document.getElementById('game-message');
    if (msgEl) {
        msgEl.textContent = message;
        msgEl.classList.add('visible');
        setTimeout(() => msgEl.classList.remove('visible'), 2000);
    }
}

function showError(message) {
    console.error('Game error:', message);
    const msgEl = document.getElementById('game-message');
    if (msgEl) {
        msgEl.textContent = message;
        msgEl.classList.add('visible', 'error');
        setTimeout(() => msgEl.classList.remove('visible', 'error'), 3000);
    }
}

// Game actions via WebSocket
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
    document.getElementById('round-result').textContent = '';
    document.getElementById('round-result').className = '';
    wsClient.newRound();
}

function resetGame() {
    statsTracker.reset();
    countTracker.reset(6);
    wsClient.send('reset_game');
}

// Navigation
function setupNavigation() {
    document.getElementById('nav-play').addEventListener('click', (e) => {
        e.preventDefault();
        switchMode('play');
    });

    document.getElementById('nav-count-drill').addEventListener('click', (e) => {
        e.preventDefault();
        switchMode('count-drill');
    });

    document.getElementById('nav-strategy-drill').addEventListener('click', (e) => {
        e.preventDefault();
        switchMode('strategy-drill');
    });

    document.getElementById('nav-settings')?.addEventListener('click', (e) => {
        e.preventDefault();
        toggleSettings();
    });
}

function switchMode(mode) {
    currentMode = mode;

    // Update nav active states
    document.querySelectorAll('footer nav a').forEach(a => a.classList.remove('active'));
    document.getElementById(`nav-${mode === 'play' ? 'play' : mode}`).classList.add('active');

    // Show/hide sections
    document.getElementById('game-area').classList.toggle('hidden', mode !== 'play');
    document.getElementById('count-drill-area')?.classList.toggle('hidden', mode !== 'count-drill');
    document.getElementById('strategy-drill-area')?.classList.toggle('hidden', mode !== 'strategy-drill');
}

// Count display toggle
function setupCountToggle() {
    const toggleBtn = document.getElementById('toggle-count');
    if (toggleBtn) {
        toggleBtn.addEventListener('click', () => {
            countVisible = !countVisible;
            document.getElementById('count-section').classList.toggle('blurred', !countVisible);
            toggleBtn.textContent = countVisible ? 'Hide Count' : 'Show Count';
        });
    }
}

function toggleSettings() {
    const settingsPanel = document.getElementById('settings-panel');
    if (settingsPanel) {
        settingsPanel.classList.toggle('hidden');
    }
}

// Counting Drill Functions
let currentDrill = null;
let drillCardIndex = 0;
let drillInterval = null;
let drillSpeed = 1500; // ms between cards

async function startCountingDrill() {
    const numCards = parseInt(document.getElementById('drill-num-cards')?.value || 10);
    const system = document.getElementById('drill-system')?.value || 'hilo';
    drillSpeed = parseInt(document.getElementById('drill-speed')?.value || 1500);

    try {
        const response = await fetch('/api/training/counting/drill', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-Session-ID': sessionId
            },
            body: JSON.stringify({ num_cards: numCards, system: system })
        });

        currentDrill = await response.json();
        drillCardIndex = 0;

        // Show drill area
        document.getElementById('drill-cards').innerHTML = '';
        document.getElementById('drill-input-area').classList.add('hidden');
        document.getElementById('drill-result').classList.add('hidden');
        document.getElementById('btn-start-drill').disabled = true;

        // Flash cards one by one
        drillInterval = setInterval(showNextDrillCard, drillSpeed);
    } catch (error) {
        console.error('Error starting drill:', error);
    }
}

function showNextDrillCard() {
    if (drillCardIndex >= currentDrill.cards.length) {
        clearInterval(drillInterval);
        // Show input for user to enter count
        document.getElementById('drill-cards').innerHTML = '<div class="drill-complete">Enter your count</div>';
        document.getElementById('drill-input-area').classList.remove('hidden');
        document.getElementById('user-count').focus();
        document.getElementById('btn-start-drill').disabled = false;
        return;
    }

    const card = currentDrill.cards[drillCardIndex];
    const cardEl = document.createElement('div');
    cardEl.className = 'drill-card';
    cardEl.innerHTML = renderCard(card);

    const container = document.getElementById('drill-cards');
    container.innerHTML = '';
    container.appendChild(cardEl);

    // Animate card
    setTimeout(() => cardEl.classList.add('visible'), 10);

    drillCardIndex++;
}

async function submitCount() {
    const userCount = parseFloat(document.getElementById('user-count').value);

    try {
        const response = await fetch('/api/training/counting/verify', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ session_id: sessionId, user_count: userCount })
        });

        const result = await response.json();

        const resultEl = document.getElementById('drill-result');
        resultEl.classList.remove('hidden');

        if (result.correct) {
            resultEl.innerHTML = `<span class="correct">Correct!</span> Count: ${result.actual_count}`;
        } else {
            resultEl.innerHTML = `<span class="incorrect">Incorrect.</span> Your answer: ${userCount}, Actual: ${result.actual_count}`;
        }

        document.getElementById('user-count').value = '';
    } catch (error) {
        console.error('Error verifying count:', error);
    }
}

// Strategy Drill Functions
let currentStrategyDrill = null;

async function startStrategyDrill() {
    const includeDeviations = document.getElementById('include-deviations')?.checked || false;
    const trueCount = includeDeviations ? parseFloat(document.getElementById('drill-true-count')?.value || 0) : null;

    try {
        const response = await fetch('/api/training/strategy/drill', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-Session-ID': sessionId
            },
            body: JSON.stringify({
                include_deviations: includeDeviations,
                true_count: trueCount
            })
        });

        currentStrategyDrill = await response.json();

        // Display the hand
        const playerCardsEl = document.getElementById('strategy-player-cards');
        playerCardsEl.innerHTML = currentStrategyDrill.player_cards.map(c => renderCard(c)).join('');

        const dealerCardEl = document.getElementById('strategy-dealer-card');
        dealerCardEl.innerHTML = renderCard(currentStrategyDrill.dealer_upcard);

        // Show hand info
        const handInfo = document.getElementById('strategy-hand-info');
        let info = `${currentStrategyDrill.is_soft ? 'Soft ' : ''}${currentStrategyDrill.player_value}`;
        if (currentStrategyDrill.is_pair) info += ' (Pair)';
        handInfo.textContent = info;

        // Reset action buttons
        document.querySelectorAll('.strategy-action-btn').forEach(btn => {
            btn.classList.remove('correct', 'incorrect', 'selected');
            btn.disabled = false;
        });

        document.getElementById('strategy-result').classList.add('hidden');
    } catch (error) {
        console.error('Error starting strategy drill:', error);
    }
}

function checkStrategyAction(action) {
    if (!currentStrategyDrill) return;

    const correctAction = currentStrategyDrill.correct_action;
    const isCorrect = action.toUpperCase() === correctAction.toUpperCase();

    // Highlight buttons
    document.querySelectorAll('.strategy-action-btn').forEach(btn => {
        const btnAction = btn.dataset.action;
        if (btnAction.toUpperCase() === correctAction.toUpperCase()) {
            btn.classList.add('correct');
        }
        if (btnAction === action && !isCorrect) {
            btn.classList.add('incorrect');
        }
        btn.disabled = true;
    });

    // Show result
    const resultEl = document.getElementById('strategy-result');
    resultEl.classList.remove('hidden');

    if (isCorrect) {
        resultEl.innerHTML = '<span class="correct">Correct!</span>';
    } else {
        resultEl.innerHTML = `<span class="incorrect">Incorrect.</span> Correct action: ${correctAction}`;
    }

    if (currentStrategyDrill.deviation) {
        resultEl.innerHTML += `<br><small>Deviation: ${currentStrategyDrill.deviation}</small>`;
    }
}

// Initialize on page load
document.addEventListener('DOMContentLoaded', initGame);

// ============================================
// STRATEGY HINTS & BETTING ADVICE SYSTEM
// ============================================

// Strategy tables - basic strategy for 6-deck S17 DAS
// Keys: dealer upcard (2-11 where 11=A), Values: action (H=Hit, S=Stand, D=Double, P=Split, R=Surrender)
const STRATEGY_TABLES = {
    // Hard totals: player total -> { dealer upcard -> action }
    hard: {
        5:  { 2:'H', 3:'H', 4:'H', 5:'H', 6:'H', 7:'H', 8:'H', 9:'H', 10:'H', 11:'H' },
        6:  { 2:'H', 3:'H', 4:'H', 5:'H', 6:'H', 7:'H', 8:'H', 9:'H', 10:'H', 11:'H' },
        7:  { 2:'H', 3:'H', 4:'H', 5:'H', 6:'H', 7:'H', 8:'H', 9:'H', 10:'H', 11:'H' },
        8:  { 2:'H', 3:'H', 4:'H', 5:'H', 6:'H', 7:'H', 8:'H', 9:'H', 10:'H', 11:'H' },
        9:  { 2:'H', 3:'D', 4:'D', 5:'D', 6:'D', 7:'H', 8:'H', 9:'H', 10:'H', 11:'H' },
        10: { 2:'D', 3:'D', 4:'D', 5:'D', 6:'D', 7:'D', 8:'D', 9:'D', 10:'H', 11:'H' },
        11: { 2:'D', 3:'D', 4:'D', 5:'D', 6:'D', 7:'D', 8:'D', 9:'D', 10:'D', 11:'D' },
        12: { 2:'H', 3:'H', 4:'S', 5:'S', 6:'S', 7:'H', 8:'H', 9:'H', 10:'H', 11:'H' },
        13: { 2:'S', 3:'S', 4:'S', 5:'S', 6:'S', 7:'H', 8:'H', 9:'H', 10:'H', 11:'H' },
        14: { 2:'S', 3:'S', 4:'S', 5:'S', 6:'S', 7:'H', 8:'H', 9:'H', 10:'H', 11:'H' },
        15: { 2:'S', 3:'S', 4:'S', 5:'S', 6:'S', 7:'H', 8:'H', 9:'H', 10:'R', 11:'R' },
        16: { 2:'S', 3:'S', 4:'S', 5:'S', 6:'S', 7:'H', 8:'H', 9:'R', 10:'R', 11:'R' },
        17: { 2:'S', 3:'S', 4:'S', 5:'S', 6:'S', 7:'S', 8:'S', 9:'S', 10:'S', 11:'S' },
        18: { 2:'S', 3:'S', 4:'S', 5:'S', 6:'S', 7:'S', 8:'S', 9:'S', 10:'S', 11:'S' },
        19: { 2:'S', 3:'S', 4:'S', 5:'S', 6:'S', 7:'S', 8:'S', 9:'S', 10:'S', 11:'S' },
        20: { 2:'S', 3:'S', 4:'S', 5:'S', 6:'S', 7:'S', 8:'S', 9:'S', 10:'S', 11:'S' },
        21: { 2:'S', 3:'S', 4:'S', 5:'S', 6:'S', 7:'S', 8:'S', 9:'S', 10:'S', 11:'S' }
    },
    // Soft totals: player total -> { dealer upcard -> action }
    soft: {
        13: { 2:'H', 3:'H', 4:'H', 5:'D', 6:'D', 7:'H', 8:'H', 9:'H', 10:'H', 11:'H' },
        14: { 2:'H', 3:'H', 4:'H', 5:'D', 6:'D', 7:'H', 8:'H', 9:'H', 10:'H', 11:'H' },
        15: { 2:'H', 3:'H', 4:'D', 5:'D', 6:'D', 7:'H', 8:'H', 9:'H', 10:'H', 11:'H' },
        16: { 2:'H', 3:'H', 4:'D', 5:'D', 6:'D', 7:'H', 8:'H', 9:'H', 10:'H', 11:'H' },
        17: { 2:'H', 3:'D', 4:'D', 5:'D', 6:'D', 7:'H', 8:'H', 9:'H', 10:'H', 11:'H' },
        18: { 2:'D', 3:'D', 4:'D', 5:'D', 6:'D', 7:'S', 8:'S', 9:'H', 10:'H', 11:'H' },
        19: { 2:'S', 3:'S', 4:'S', 5:'S', 6:'D', 7:'S', 8:'S', 9:'S', 10:'S', 11:'S' },
        20: { 2:'S', 3:'S', 4:'S', 5:'S', 6:'S', 7:'S', 8:'S', 9:'S', 10:'S', 11:'S' },
        21: { 2:'S', 3:'S', 4:'S', 5:'S', 6:'S', 7:'S', 8:'S', 9:'S', 10:'S', 11:'S' }
    },
    // Pairs: pair rank (2-11 where 11=A) -> { dealer upcard -> action }
    pairs: {
        2:  { 2:'P', 3:'P', 4:'P', 5:'P', 6:'P', 7:'P', 8:'H', 9:'H', 10:'H', 11:'H' },
        3:  { 2:'P', 3:'P', 4:'P', 5:'P', 6:'P', 7:'P', 8:'H', 9:'H', 10:'H', 11:'H' },
        4:  { 2:'H', 3:'H', 4:'H', 5:'P', 6:'P', 7:'H', 8:'H', 9:'H', 10:'H', 11:'H' },
        5:  { 2:'D', 3:'D', 4:'D', 5:'D', 6:'D', 7:'D', 8:'D', 9:'D', 10:'H', 11:'H' },
        6:  { 2:'P', 3:'P', 4:'P', 5:'P', 6:'P', 7:'H', 8:'H', 9:'H', 10:'H', 11:'H' },
        7:  { 2:'P', 3:'P', 4:'P', 5:'P', 6:'P', 7:'P', 8:'H', 9:'H', 10:'H', 11:'H' },
        8:  { 2:'P', 3:'P', 4:'P', 5:'P', 6:'P', 7:'P', 8:'P', 9:'P', 10:'P', 11:'P' },
        9:  { 2:'P', 3:'P', 4:'P', 5:'P', 6:'P', 7:'S', 8:'P', 9:'P', 10:'S', 11:'S' },
        10: { 2:'S', 3:'S', 4:'S', 5:'S', 6:'S', 7:'S', 8:'S', 9:'S', 10:'S', 11:'S' },
        11: { 2:'P', 3:'P', 4:'P', 5:'P', 6:'P', 7:'P', 8:'P', 9:'P', 10:'P', 11:'P' }
    }
};

// Illustrious 18 + Fab 4 deviations
// Format: { key: 'playerTotal-dealerUpcard-handType', threshold: TC, action: 'action', direction: 'gte'|'lte' }
const DEVIATIONS = [
    // Illustrious 18
    { key: '16-10-hard', threshold: 0, action: 'S', direction: 'gte', description: 'Stand 16 vs 10 at TC 0+' },
    { key: '15-10-hard', threshold: 4, action: 'S', direction: 'gte', description: 'Stand 15 vs 10 at TC +4+' },
    { key: '10-10-hard', threshold: 4, action: 'D', direction: 'gte', description: 'Double 10 vs 10 at TC +4+' },
    { key: '10-11-hard', threshold: 4, action: 'D', direction: 'gte', description: 'Double 10 vs A at TC +4+' },
    { key: '12-3-hard', threshold: 2, action: 'S', direction: 'gte', description: 'Stand 12 vs 3 at TC +2+' },
    { key: '12-2-hard', threshold: 3, action: 'S', direction: 'gte', description: 'Stand 12 vs 2 at TC +3+' },
    { key: '12-4-hard', threshold: 0, action: 'H', direction: 'lte', description: 'Hit 12 vs 4 at TC 0 or less' },
    { key: '12-5-hard', threshold: -2, action: 'H', direction: 'lte', description: 'Hit 12 vs 5 at TC -2 or less' },
    { key: '12-6-hard', threshold: -1, action: 'H', direction: 'lte', description: 'Hit 12 vs 6 at TC -1 or less' },
    { key: '13-2-hard', threshold: -1, action: 'H', direction: 'lte', description: 'Hit 13 vs 2 at TC -1 or less' },
    { key: '13-3-hard', threshold: -2, action: 'H', direction: 'lte', description: 'Hit 13 vs 3 at TC -2 or less' },
    { key: '11-11-hard', threshold: 1, action: 'D', direction: 'gte', description: 'Double 11 vs A at TC +1+' },
    { key: '9-2-hard', threshold: 1, action: 'D', direction: 'gte', description: 'Double 9 vs 2 at TC +1+' },
    { key: '9-7-hard', threshold: 3, action: 'D', direction: 'gte', description: 'Double 9 vs 7 at TC +3+' },
    { key: '10-11-hard', threshold: 4, action: 'D', direction: 'gte', description: 'Double 10 vs A at TC +4+' },
    { key: '8-6-hard', threshold: 2, action: 'D', direction: 'gte', description: 'Double 8 vs 6 at TC +2+' },
    // Insurance (not directly used but noted)
    // Fab 4 Surrenders
    { key: '14-10-hard', threshold: 3, action: 'R', direction: 'gte', description: 'Surrender 14 vs 10 at TC +3+' },
    { key: '15-9-hard', threshold: 2, action: 'R', direction: 'gte', description: 'Surrender 15 vs 9 at TC +2+' },
    { key: '15-11-hard', threshold: 1, action: 'R', direction: 'gte', description: 'Surrender 15 vs A at TC +1+' },
    { key: '14-11-hard', threshold: 3, action: 'R', direction: 'gte', description: 'Surrender 14 vs A at TC +3+' }
];

// Hint visibility state
let bestPlayHintEnabled = true;
let betHintsEnabled = true;
let currentGameState = null;

// ============================================
// STRATEGY CHART MODAL
// ============================================

function openStrategyChart() {
    const modal = document.getElementById('strategy-chart-modal');
    if (!modal) return;

    generateStrategyCharts();
    setupChartTabs();
    modal.classList.remove('hidden');

    // Highlight current hand if in player turn
    if (currentGameState?.state === 'PLAYER_TURN') {
        highlightCurrentHand();
    }
}

function closeStrategyChart() {
    const modal = document.getElementById('strategy-chart-modal');
    if (modal) {
        modal.classList.add('hidden');
    }
}

function generateStrategyCharts() {
    generateHardChart();
    generateSoftChart();
    generatePairsChart();
}

function generateHardChart() {
    const container = document.getElementById('chart-hard');
    if (!container) return;

    const dealerCards = [2, 3, 4, 5, 6, 7, 8, 9, 10, 11];
    const playerTotals = [8, 9, 10, 11, 12, 13, 14, 15, 16, 17];

    // Grid: 11 columns (row header + 10 dealer cards), rows for each player total + header
    container.style.gridTemplateColumns = `repeat(${dealerCards.length + 1}, 1fr)`;

    let html = '<div class="chart-cell chart-header"></div>';
    dealerCards.forEach(d => {
        html += `<div class="chart-cell chart-header">${d === 11 ? 'A' : d}</div>`;
    });

    playerTotals.forEach(total => {
        html += `<div class="chart-cell chart-row-header">${total}</div>`;
        dealerCards.forEach(dealer => {
            const action = STRATEGY_TABLES.hard[total]?.[dealer] || 'H';
            const actionClass = getActionClass(action);
            html += `<div class="chart-cell ${actionClass}" data-player="${total}" data-dealer="${dealer}" data-type="hard">${action}</div>`;
        });
    });

    container.innerHTML = html;
}

function generateSoftChart() {
    const container = document.getElementById('chart-soft');
    if (!container) return;

    const dealerCards = [2, 3, 4, 5, 6, 7, 8, 9, 10, 11];
    const playerTotals = [13, 14, 15, 16, 17, 18, 19, 20];

    container.style.gridTemplateColumns = `repeat(${dealerCards.length + 1}, 1fr)`;

    let html = '<div class="chart-cell chart-header"></div>';
    dealerCards.forEach(d => {
        html += `<div class="chart-cell chart-header">${d === 11 ? 'A' : d}</div>`;
    });

    playerTotals.forEach(total => {
        html += `<div class="chart-cell chart-row-header">A,${total - 11}</div>`;
        dealerCards.forEach(dealer => {
            const action = STRATEGY_TABLES.soft[total]?.[dealer] || 'H';
            const actionClass = getActionClass(action);
            html += `<div class="chart-cell ${actionClass}" data-player="${total}" data-dealer="${dealer}" data-type="soft">${action}</div>`;
        });
    });

    container.innerHTML = html;
}

function generatePairsChart() {
    const container = document.getElementById('chart-pairs');
    if (!container) return;

    const dealerCards = [2, 3, 4, 5, 6, 7, 8, 9, 10, 11];
    const pairRanks = [2, 3, 4, 5, 6, 7, 8, 9, 10, 11];

    container.style.gridTemplateColumns = `repeat(${dealerCards.length + 1}, 1fr)`;

    let html = '<div class="chart-cell chart-header"></div>';
    dealerCards.forEach(d => {
        html += `<div class="chart-cell chart-header">${d === 11 ? 'A' : d}</div>`;
    });

    pairRanks.forEach(rank => {
        const displayRank = rank === 11 ? 'A,A' : `${rank},${rank}`;
        html += `<div class="chart-cell chart-row-header">${displayRank}</div>`;
        dealerCards.forEach(dealer => {
            const action = STRATEGY_TABLES.pairs[rank]?.[dealer] || 'H';
            const actionClass = getActionClass(action);
            html += `<div class="chart-cell ${actionClass}" data-player="${rank}" data-dealer="${dealer}" data-type="pairs">${action}</div>`;
        });
    });

    container.innerHTML = html;
}

function getActionClass(action) {
    const classes = {
        'H': 'action-hit',
        'S': 'action-stand',
        'D': 'action-double',
        'P': 'action-split',
        'R': 'action-surrender'
    };
    return classes[action] || 'action-hit';
}

function setupChartTabs() {
    const tabs = document.querySelectorAll('.chart-tab');
    tabs.forEach(tab => {
        tab.addEventListener('click', () => {
            const tabName = tab.dataset.tab;

            // Update tab active states
            tabs.forEach(t => t.classList.remove('active'));
            tab.classList.add('active');

            // Show correct chart
            document.querySelectorAll('.chart-grid').forEach(grid => grid.classList.add('hidden'));
            document.getElementById(`chart-${tabName}`)?.classList.remove('hidden');

            // Re-highlight if applicable
            if (currentGameState?.state === 'PLAYER_TURN') {
                highlightCurrentHand();
            }
        });
    });
}

function highlightCurrentHand() {
    // Remove previous highlights
    document.querySelectorAll('.chart-cell.highlighted').forEach(cell => {
        cell.classList.remove('highlighted');
    });

    if (!currentGameState || currentGameState.state !== 'PLAYER_TURN') return;

    const handInfo = getHandInfo(currentGameState);
    if (!handInfo) return;

    const { playerValue, dealerUpcard, isPair, isSoft, pairRank } = handInfo;

    // Determine which chart and which cell
    let chartType, playerKey;
    if (isPair) {
        chartType = 'pairs';
        playerKey = pairRank;
    } else if (isSoft) {
        chartType = 'soft';
        playerKey = playerValue;
    } else {
        chartType = 'hard';
        playerKey = playerValue;
    }

    // Find and highlight the cell
    const cell = document.querySelector(`.chart-cell[data-player="${playerKey}"][data-dealer="${dealerUpcard}"][data-type="${chartType}"]`);
    if (cell) {
        cell.classList.add('highlighted');

        // Switch to the correct tab
        document.querySelectorAll('.chart-tab').forEach(t => t.classList.remove('active'));
        document.querySelector(`.chart-tab[data-tab="${chartType}"]`)?.classList.add('active');
        document.querySelectorAll('.chart-grid').forEach(g => g.classList.add('hidden'));
        document.getElementById(`chart-${chartType}`)?.classList.remove('hidden');
    }
}

// ============================================
// BEST PLAY TOOLTIP
// ============================================

function getBestPlay(handInfo, trueCount = 0) {
    const { playerValue, dealerUpcard, isPair, isSoft, pairRank } = handInfo;

    // Check for deviation first
    const deviation = checkDeviation(playerValue, dealerUpcard, isSoft, isPair, trueCount);
    if (deviation) {
        return {
            action: deviation.action,
            reason: deviation.description,
            isDeviation: true
        };
    }

    // Look up basic strategy
    let action;
    let handType;

    if (isPair) {
        action = STRATEGY_TABLES.pairs[pairRank]?.[dealerUpcard];
        handType = `Pair of ${pairRank === 11 ? 'Aces' : pairRank}s`;
    } else if (isSoft) {
        action = STRATEGY_TABLES.soft[playerValue]?.[dealerUpcard];
        handType = `Soft ${playerValue}`;
    } else {
        action = STRATEGY_TABLES.hard[playerValue]?.[dealerUpcard];
        handType = `Hard ${playerValue}`;
    }

    if (!action) {
        action = playerValue >= 17 ? 'S' : 'H';
    }

    const actionNames = { 'H': 'HIT', 'S': 'STAND', 'D': 'DOUBLE', 'P': 'SPLIT', 'R': 'SURRENDER' };

    return {
        action: action,
        reason: `${actionNames[action]} - ${handType}`,
        isDeviation: false
    };
}

function checkDeviation(playerValue, dealerUpcard, isSoft, isPair, trueCount) {
    if (isPair) return null; // No pair deviations in I18/Fab4

    const handType = isSoft ? 'soft' : 'hard';
    const key = `${playerValue}-${dealerUpcard}-${handType}`;

    for (const dev of DEVIATIONS) {
        if (dev.key === key) {
            const shouldApply = dev.direction === 'gte'
                ? trueCount >= dev.threshold
                : trueCount <= dev.threshold;

            if (shouldApply) {
                return dev;
            }
        }
    }

    return null;
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

    // Update action display
    const actionNames = { 'H': 'HIT', 'S': 'STAND', 'D': 'DOUBLE', 'P': 'SPLIT', 'R': 'SURRENDER' };
    actionEl.textContent = actionNames[bestPlay.action] || bestPlay.action;
    actionEl.className = `tooltip-action action-${getActionClass(bestPlay.action).replace('action-', '')}`;

    // Update reason
    reasonEl.textContent = bestPlay.reason;

    // Handle deviation badge
    if (bestPlay.isDeviation) {
        devBadge.classList.remove('hidden');
        tooltip.classList.add('has-deviation');
    } else {
        devBadge.classList.add('hidden');
        tooltip.classList.remove('has-deviation');
    }

    tooltip.classList.remove('hidden');
}

function getHandInfo(state) {
    if (!state?.player_hands || state.player_hands.length === 0) return null;

    const handIndex = state.current_hand_index || 0;
    const hand = state.player_hands[handIndex];
    if (!hand || !hand.cards || hand.cards.length < 2) return null;

    const dealerShowing = state.dealer_showing || getDealerUpcard(state);
    if (!dealerShowing) return null;

    // Convert dealer showing to numeric value
    let dealerUpcard = dealerShowing;
    if (typeof dealerUpcard === 'string') {
        const rankMap = { 'A': 11, 'K': 10, 'Q': 10, 'J': 10, 'T': 10 };
        dealerUpcard = rankMap[dealerUpcard] || parseInt(dealerUpcard, 10);
    }

    // Check if pair
    let isPair = false;
    let pairRank = null;
    if (hand.cards.length === 2) {
        const rank1 = getCardNumericRank(hand.cards[0]);
        const rank2 = getCardNumericRank(hand.cards[1]);
        if (rank1 === rank2) {
            isPair = true;
            pairRank = rank1;
        }
    }

    return {
        playerValue: hand.value,
        dealerUpcard: dealerUpcard,
        isPair: isPair,
        isSoft: hand.is_soft,
        pairRank: pairRank
    };
}

function getDealerUpcard(state) {
    if (!state?.dealer_hand?.cards) return null;
    const visibleCard = state.dealer_hand.cards.find(c => !c.hidden && c.rank !== '?');
    if (!visibleCard) return null;
    return getCardNumericRank(visibleCard);
}

function getCardNumericRank(card) {
    if (!card || !card.rank) return null;
    const rankMap = {
        'ACE': 11, 'KING': 10, 'QUEEN': 10, 'JACK': 10, 'TEN': 10,
        'NINE': 9, 'EIGHT': 8, 'SEVEN': 7, 'SIX': 6, 'FIVE': 5,
        'FOUR': 4, 'THREE': 3, 'TWO': 2,
        'A': 11, 'K': 10, 'Q': 10, 'J': 10, 'T': 10,
        '10': 10, '9': 9, '8': 8, '7': 7, '6': 6, '5': 5, '4': 4, '3': 3, '2': 2
    };
    return rankMap[card.rank] || parseInt(card.rank, 10) || null;
}

// ============================================
// BETTING HINTS
// ============================================

function getBettingHint(trueCount) {
    // Each TC point ≈ 0.5% edge change
    // House edge at TC 0 ≈ -0.5%
    // Breakeven around TC +1

    const baseEdge = -0.5;
    const edgePerTC = 0.5;
    const playerEdge = baseEdge + (trueCount * edgePerTC);

    let units, level, message;

    if (trueCount < 1) {
        units = 1;
        level = 'negative';
        message = '1 unit - House edge';
    } else if (trueCount < 2) {
        units = 1;
        level = 'breakeven';
        message = '1 unit - Breakeven zone';
    } else if (trueCount < 3) {
        units = 2;
        level = 'positive';
        message = '2 units - Player advantage';
    } else if (trueCount < 4) {
        units = 4;
        level = 'positive';
        message = '4 units - Player advantage';
    } else if (trueCount < 5) {
        units = 6;
        level = 'strong';
        message = '6 units - Strong advantage';
    } else {
        units = Math.min(12, Math.floor(trueCount * 1.5));
        level = 'strong';
        message = `${units} units - Strong advantage`;
    }

    return {
        units: units,
        level: level,
        message: message,
        edge: playerEdge,
        trueCount: trueCount
    };
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

    // Update hint display
    hintEl.querySelector('.hint-units').textContent = hint.message;
    hintEl.querySelector('.hint-edge').textContent = `Player edge: ${hint.edge >= 0 ? '+' : ''}${hint.edge.toFixed(1)}%`;
    hintEl.querySelector('.hint-count span').textContent = trueCount.toFixed(1);

    // Update advantage level class
    hintEl.className = '';
    hintEl.classList.add(`advantage-${hint.level}`);

    hintEl.classList.remove('hidden');
}

// ============================================
// HINT TOGGLES
// ============================================

function toggleBestPlayHint() {
    bestPlayHintEnabled = document.getElementById('toggle-best-play')?.checked ?? true;
    if (currentGameState) {
        updateBestPlayTooltip(currentGameState);
    }
}

function toggleBetHints() {
    betHintsEnabled = document.getElementById('toggle-bet-hints')?.checked ?? true;
    if (currentGameState) {
        updateBettingHint(currentGameState);
    }
}

// ============================================
// KEYBOARD HANDLERS
// ============================================

document.addEventListener('keydown', (e) => {
    // Handle modal controls first
    if (e.key === 'Escape') {
        closeStrategyChart();
        return;
    }

    // Strategy chart toggle
    if (e.key.toLowerCase() === 'c' && document.activeElement.tagName !== 'INPUT') {
        const modal = document.getElementById('strategy-chart-modal');
        if (modal?.classList.contains('hidden')) {
            openStrategyChart();
        } else {
            closeStrategyChart();
        }
        return;
    }

    // Original game controls
    if (currentMode !== 'play') return;
    if (document.activeElement.tagName === 'INPUT') return;

    // Don't process if modal is open
    if (!document.getElementById('strategy-chart-modal')?.classList.contains('hidden')) return;

    switch(e.key.toLowerCase()) {
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
            if (!document.getElementById('result-controls').classList.contains('hidden')) newRound();
            break;
    }
});

// Click outside modal to close
document.addEventListener('click', (e) => {
    const modal = document.getElementById('strategy-chart-modal');
    if (!modal || modal.classList.contains('hidden')) return;

    // If click is on the modal backdrop (not the content), close it
    if (e.target === modal) {
        closeStrategyChart();
    }
});

// Hook into renderGameState to update hints
const originalRenderGameState = renderGameState;
window.renderGameState = function(state) {
    currentGameState = state;
    originalRenderGameState(state);

    // Update hints
    updateBestPlayTooltip(state);
    updateBettingHint(state);

    // Update chart highlight if open
    if (!document.getElementById('strategy-chart-modal')?.classList.contains('hidden')) {
        highlightCurrentHand();
    }
};

// Expose functions globally for onclick handlers
window.placeBet = placeBet;
window.playerAction = playerAction;
window.newRound = newRound;
window.resetGame = resetGame;
window.startCountingDrill = startCountingDrill;
window.submitCount = submitCount;
window.startStrategyDrill = startStrategyDrill;
window.checkStrategyAction = checkStrategyAction;
window.openStrategyChart = openStrategyChart;
window.closeStrategyChart = closeStrategyChart;
window.toggleBestPlayHint = toggleBestPlayHint;
window.toggleBetHints = toggleBetHints;
