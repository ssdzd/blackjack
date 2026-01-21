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
    const insuranceControls = document.getElementById('insurance-controls');

    // Hide all first
    bettingControls.classList.add('hidden');
    actionControls.classList.add('hidden');
    resultControls.classList.add('hidden');
    insuranceControls?.classList.add('hidden');

    switch (state.state) {
        case 'WAITING_FOR_BET':
            bettingControls.classList.remove('hidden');
            // Clear any previous result
            document.getElementById('round-result').textContent = '';
            document.getElementById('round-result').className = '';
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

// Insurance functions
function takeInsurance() {
    wsClient.send('insurance', { take: true });
}

function declineInsurance() {
    wsClient.send('insurance', { take: false });
}

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

    document.getElementById('nav-performance')?.addEventListener('click', (e) => {
        e.preventDefault();
        switchMode('performance');
        refreshPerformanceStats();
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
    document.getElementById('performance-area')?.classList.toggle('hidden', mode !== 'performance');
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
let speedModeEnabled = false;
let speedDrillStartTime = null;
let speedTimerInterval = null;
let highScores = JSON.parse(localStorage.getItem('speedDrillHighScores') || '[]');

function toggleSpeedMode() {
    speedModeEnabled = document.getElementById('speed-mode')?.checked || false;
    const speedInfo = document.getElementById('speed-drill-info');
    const scoresEl = document.getElementById('speed-drill-scores');

    if (speedModeEnabled) {
        speedInfo?.classList.remove('hidden');
        scoresEl?.classList.remove('hidden');
        updateHighScoresDisplay();
    } else {
        speedInfo?.classList.add('hidden');
        scoresEl?.classList.add('hidden');
    }
}

async function startCountingDrill() {
    const numCards = parseInt(document.getElementById('drill-num-cards')?.value || 10);
    const system = document.getElementById('drill-system')?.value || 'hilo';
    drillSpeed = parseInt(document.getElementById('drill-speed')?.value || 1500);

    // Use different endpoint for speed drill
    const endpoint = speedModeEnabled
        ? '/api/training/counting/speed-drill'
        : '/api/training/counting/drill';

    const body = speedModeEnabled
        ? { num_cards: numCards, system: system, card_speed_ms: drillSpeed }
        : { num_cards: numCards, system: system };

    try {
        const response = await fetch(endpoint, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-Session-ID': sessionId
            },
            body: JSON.stringify(body)
        });

        currentDrill = await response.json();
        drillCardIndex = 0;

        // Show drill area
        document.getElementById('drill-cards').innerHTML = '';
        document.getElementById('drill-input-area').classList.add('hidden');
        document.getElementById('drill-result').classList.add('hidden');
        document.getElementById('btn-start-drill').disabled = true;

        // Start speed timer if in speed mode
        if (speedModeEnabled) {
            speedDrillStartTime = Date.now();
            startSpeedTimer();
            updateCardProgress(0, currentDrill.cards.length);
        }

        // Flash cards one by one
        drillInterval = setInterval(showNextDrillCard, drillSpeed);
    } catch (error) {
        console.error('Error starting drill:', error);
    }
}

function startSpeedTimer() {
    const timerDisplay = document.getElementById('speed-timer-display');
    if (!timerDisplay) return;

    speedTimerInterval = setInterval(() => {
        const elapsed = (Date.now() - speedDrillStartTime) / 1000;
        timerDisplay.textContent = `${elapsed.toFixed(2)}s`;
    }, 50);
}

function stopSpeedTimer() {
    if (speedTimerInterval) {
        clearInterval(speedTimerInterval);
        speedTimerInterval = null;
    }
}

function updateCardProgress(current, total) {
    const progressEl = document.getElementById('speed-card-progress');
    if (progressEl) {
        progressEl.textContent = `${current}/${total}`;
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

        // Update progress for speed mode
        if (speedModeEnabled) {
            updateCardProgress(currentDrill.cards.length, currentDrill.cards.length);
        }
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

    // Update progress for speed mode
    if (speedModeEnabled) {
        updateCardProgress(drillCardIndex, currentDrill.cards.length);
    }
}

async function submitCount() {
    const userCount = parseFloat(document.getElementById('user-count').value);

    // Stop timer for speed mode
    stopSpeedTimer();
    const completionTime = speedModeEnabled ? Date.now() - speedDrillStartTime : 0;

    // Use different endpoint for speed drill
    if (speedModeEnabled && currentDrill.drill_id) {
        try {
            const response = await fetch('/api/training/counting/speed-drill/verify', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    drill_id: currentDrill.drill_id,
                    user_count: userCount,
                    completion_time_ms: completionTime
                })
            });

            const result = await response.json();

            const resultEl = document.getElementById('drill-result');
            resultEl.classList.remove('hidden');

            if (result.correct) {
                resultEl.innerHTML = `
                    <div class="speed-result-correct">
                        <span class="correct">Correct!</span>
                        <div class="speed-score">Score: ${result.score}</div>
                        <div class="speed-breakdown">
                            Base: ${result.breakdown.base} |
                            Time Bonus: ${result.breakdown.time_bonus} |
                            Accuracy: ${result.breakdown.accuracy}
                        </div>
                        <div class="speed-time">Time: ${(result.completion_time_ms / 1000).toFixed(2)}s</div>
                    </div>`;

                // Save high score
                saveHighScore(result.score, result.completion_time_ms, currentDrill.num_cards);
            } else {
                resultEl.innerHTML = `
                    <div class="speed-result-incorrect">
                        <span class="incorrect">Incorrect.</span>
                        <div>Your answer: ${userCount}, Actual: ${result.actual_count}</div>
                        <div class="speed-score">Score: ${result.score}</div>
                        <div class="speed-time">Time: ${(result.completion_time_ms / 1000).toFixed(2)}s</div>
                    </div>`;
            }

            document.getElementById('user-count').value = '';
        } catch (error) {
            console.error('Error verifying speed drill:', error);
        }
    } else {
        // Standard counting drill
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
}

function saveHighScore(score, timeMs, numCards) {
    const entry = {
        score: score,
        time_ms: timeMs,
        num_cards: numCards,
        date: new Date().toISOString()
    };

    highScores.push(entry);
    // Keep top 10 scores
    highScores.sort((a, b) => b.score - a.score);
    highScores = highScores.slice(0, 10);

    localStorage.setItem('speedDrillHighScores', JSON.stringify(highScores));
    updateHighScoresDisplay();
}

function updateHighScoresDisplay() {
    const listEl = document.getElementById('high-scores-list');
    if (!listEl) return;

    if (highScores.length === 0) {
        listEl.innerHTML = '<p class="no-scores">No scores yet. Complete a speed drill!</p>';
        return;
    }

    listEl.innerHTML = highScores.slice(0, 5).map((s, i) => `
        <div class="high-score-entry">
            <span class="rank">#${i + 1}</span>
            <span class="score">${s.score}</span>
            <span class="details">${s.num_cards} cards | ${(s.time_ms / 1000).toFixed(1)}s</span>
        </div>
    `).join('');
}

// Strategy Drill Functions
let currentStrategyDrill = null;
let deviationFocusMode = false;

function toggleDeviationSettings() {
    const includeDeviations = document.getElementById('include-deviations')?.checked || false;
    document.querySelector('.deviation-setting')?.classList.toggle('hidden', !includeDeviations);
}

function toggleDeviationFocus() {
    deviationFocusMode = document.getElementById('deviation-focus-mode')?.checked || false;
    document.querySelector('.deviation-focus-setting')?.classList.toggle('hidden', !deviationFocusMode);

    // If deviation focus is on, auto-enable deviations
    if (deviationFocusMode) {
        document.getElementById('include-deviations').checked = true;
        toggleDeviationSettings();
    }
}

async function startStrategyDrill() {
    const includeDeviations = document.getElementById('include-deviations')?.checked || false;
    const deviationFocus = document.getElementById('deviation-focus-mode')?.checked || false;

    // Hide deviation explanation
    document.getElementById('deviation-explanation')?.classList.add('hidden');
    document.getElementById('deviation-tc-display').style.display = 'none';

    if (deviationFocus) {
        // Use deviation-focused drill endpoint
        const tcMin = parseFloat(document.getElementById('tc-range-min')?.value || -5);
        const tcMax = parseFloat(document.getElementById('tc-range-max')?.value || 10);

        try {
            const response = await fetch('/api/training/strategy/deviation-drill', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-Session-ID': sessionId
                },
                body: JSON.stringify({
                    true_count_range_min: tcMin,
                    true_count_range_max: tcMax,
                    include_fab4: true
                })
            });

            currentStrategyDrill = await response.json();
            currentStrategyDrill.is_deviation_drill = true;

            // Display the hand
            renderStrategyDrillHand();

            // Show TC display
            document.getElementById('deviation-tc-display').style.display = 'block';
            const tcEl = document.getElementById('current-tc');
            tcEl.textContent = `TC: ${currentStrategyDrill.true_count >= 0 ? '+' : ''}${currentStrategyDrill.true_count.toFixed(0)}`;
            tcEl.className = `tc-display ${currentStrategyDrill.true_count >= 0 ? 'positive' : 'negative'}`;

        } catch (error) {
            console.error('Error starting deviation drill:', error);
        }
    } else {
        // Standard strategy drill
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
            currentStrategyDrill.is_deviation_drill = false;

            // Display the hand
            renderStrategyDrillHand();

            // Show TC if deviations enabled
            if (includeDeviations && trueCount !== null) {
                document.getElementById('deviation-tc-display').style.display = 'block';
                const tcEl = document.getElementById('current-tc');
                tcEl.textContent = `TC: ${trueCount >= 0 ? '+' : ''}${trueCount.toFixed(0)}`;
                tcEl.className = `tc-display ${trueCount >= 0 ? 'positive' : 'negative'}`;
            }

        } catch (error) {
            console.error('Error starting strategy drill:', error);
        }
    }
}

function renderStrategyDrillHand() {
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

    // Show deviation info
    const explanationEl = document.getElementById('deviation-explanation');
    if (currentStrategyDrill.is_deviation_drill) {
        const drill = currentStrategyDrill;
        const directionText = drill.direction === 'at_or_above' ? 'at or above' : 'at or below';
        const tcNeeded = drill.direction === 'at_or_above'
            ? `TC ${drill.index_threshold >= 0 ? '+' : ''}${drill.index_threshold}`
            : `TC ${drill.index_threshold}`;

        explanationEl.innerHTML = `
            <div class="deviation-info">
                <div class="deviation-name">${drill.deviation_name}</div>
                <div class="deviation-details">
                    <span>Basic Strategy: <strong>${drill.basic_strategy_action}</strong></span>
                    <span>Deviation: <strong>${drill.deviation_action}</strong> ${directionText} ${tcNeeded}</span>
                </div>
                <div class="deviation-current-tc">
                    Current TC: <strong>${drill.true_count >= 0 ? '+' : ''}${drill.true_count.toFixed(0)}</strong>
                    → ${drill.true_count >= drill.index_threshold == (drill.direction === 'at_or_above') ? 'DEVIATE' : 'BASIC STRATEGY'}
                </div>
            </div>
        `;
        explanationEl.classList.remove('hidden');
    } else if (currentStrategyDrill.deviation) {
        explanationEl.innerHTML = `<small>Deviation: ${currentStrategyDrill.deviation}</small>`;
        explanationEl.classList.remove('hidden');
    } else {
        explanationEl.classList.add('hidden');
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
            // N = New round OR No insurance depending on state
            if (!document.getElementById('result-controls').classList.contains('hidden')) {
                newRound();
            } else if (!document.getElementById('insurance-controls')?.classList.contains('hidden')) {
                declineInsurance();
            }
            break;
        case 'i':
            // I = Take insurance
            if (!document.getElementById('insurance-controls')?.classList.contains('hidden')) {
                if (!document.getElementById('btn-take-insurance').disabled) takeInsurance();
            }
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
window.takeInsurance = takeInsurance;
window.declineInsurance = declineInsurance;
window.startCountingDrill = startCountingDrill;
window.submitCount = submitCount;
window.toggleSpeedMode = toggleSpeedMode;
window.startStrategyDrill = startStrategyDrill;
window.checkStrategyAction = checkStrategyAction;
window.toggleDeviationSettings = toggleDeviationSettings;
window.toggleDeviationFocus = toggleDeviationFocus;
window.openStrategyChart = openStrategyChart;
window.closeStrategyChart = closeStrategyChart;
window.toggleBestPlayHint = toggleBestPlayHint;
window.toggleBetHints = toggleBetHints;
window.refreshPerformanceStats = refreshPerformanceStats;
window.resetPerformanceStats = resetPerformanceStats;

// ============================================
// PERFORMANCE TRACKING
// ============================================

async function refreshPerformanceStats() {
    try {
        const response = await fetch(`/api/stats/performance/${sessionId}`);
        const stats = await response.json();
        renderPerformanceStats(stats);
    } catch (error) {
        console.error('Error fetching performance stats:', error);
    }
}

async function resetPerformanceStats() {
    if (!confirm('Are you sure you want to reset all performance stats?')) {
        return;
    }

    try {
        const response = await fetch(`/api/stats/performance/${sessionId}`, {
            method: 'DELETE'
        });
        const stats = await response.json();
        renderPerformanceStats(stats);
    } catch (error) {
        console.error('Error resetting performance stats:', error);
    }
}

function renderPerformanceStats(stats) {
    // Game stats
    document.getElementById('perf-hands-played').textContent = stats.hands_played;

    const winRate = stats.hands_played > 0
        ? ((stats.wins / stats.hands_played) * 100).toFixed(1)
        : 0;
    document.getElementById('perf-win-rate').textContent = `${winRate}%`;

    const netResultEl = document.getElementById('perf-net-result');
    netResultEl.textContent = `$${stats.net_result.toFixed(0)}`;
    netResultEl.className = stats.net_result >= 0 ? 'positive' : 'negative';

    document.getElementById('perf-blackjacks').textContent = stats.blackjacks;

    // Drill accuracy
    if (stats.count_drills_attempted > 0) {
        const countAcc = ((stats.count_drills_correct / stats.count_drills_attempted) * 100).toFixed(0);
        document.getElementById('perf-count-accuracy').textContent = `${countAcc}% (${stats.count_drills_correct}/${stats.count_drills_attempted})`;
    } else {
        document.getElementById('perf-count-accuracy').textContent = '-';
    }

    if (stats.strategy_drills_attempted > 0) {
        const stratAcc = ((stats.strategy_drills_correct / stats.strategy_drills_attempted) * 100).toFixed(0);
        document.getElementById('perf-strategy-accuracy').textContent = `${stratAcc}% (${stats.strategy_drills_correct}/${stats.strategy_drills_attempted})`;
    } else {
        document.getElementById('perf-strategy-accuracy').textContent = '-';
    }

    if (stats.deviation_drills_attempted > 0) {
        const devAcc = ((stats.deviation_drills_correct / stats.deviation_drills_attempted) * 100).toFixed(0);
        document.getElementById('perf-deviation-accuracy').textContent = `${devAcc}% (${stats.deviation_drills_correct}/${stats.deviation_drills_attempted})`;
    } else {
        document.getElementById('perf-deviation-accuracy').textContent = '-';
    }

    if (stats.speed_drill_best_score > 0) {
        document.getElementById('perf-speed-best').textContent = `${stats.speed_drill_best_score} pts`;
    } else {
        document.getElementById('perf-speed-best').textContent = '-';
    }

    // Render charts
    renderBankrollChart(stats.history);
    renderDrillChart(stats);
}

function renderBankrollChart(history) {
    const canvas = document.getElementById('bankroll-chart');
    if (!canvas) return;

    const ctx = canvas.getContext('2d');
    const width = canvas.width;
    const height = canvas.height;
    const padding = 40;

    // Clear canvas
    ctx.clearRect(0, 0, width, height);

    if (!history || history.length === 0) {
        ctx.fillStyle = 'rgba(255,255,255,0.5)';
        ctx.textAlign = 'center';
        ctx.fillText('No data yet. Play some hands to see your bankroll history!', width / 2, height / 2);
        return;
    }

    // Filter for hand results only
    const handHistory = history.filter(h =>
        ['hand_win', 'hand_loss', 'hand_push', 'hand_blackjack'].includes(h.event_type)
    );

    if (handHistory.length === 0) {
        ctx.fillStyle = 'rgba(255,255,255,0.5)';
        ctx.textAlign = 'center';
        ctx.fillText('No hand history yet.', width / 2, height / 2);
        return;
    }

    // Calculate running bankroll
    const points = [];
    let bankroll = 1000;
    handHistory.forEach((h, i) => {
        bankroll = h.bankroll + 1000; // Approximate
        points.push({ x: i, y: bankroll });
    });

    // Find min/max
    const minY = Math.min(...points.map(p => p.y), 0);
    const maxY = Math.max(...points.map(p => p.y), 1000);
    const range = maxY - minY || 1;

    // Draw axes
    ctx.strokeStyle = 'rgba(255,255,255,0.3)';
    ctx.beginPath();
    ctx.moveTo(padding, padding);
    ctx.lineTo(padding, height - padding);
    ctx.lineTo(width - padding, height - padding);
    ctx.stroke();

    // Draw line
    ctx.strokeStyle = points[points.length - 1].y >= 1000 ? '#28a745' : '#dc3545';
    ctx.lineWidth = 2;
    ctx.beginPath();

    points.forEach((p, i) => {
        const x = padding + (p.x / (points.length - 1 || 1)) * (width - 2 * padding);
        const y = height - padding - ((p.y - minY) / range) * (height - 2 * padding);

        if (i === 0) {
            ctx.moveTo(x, y);
        } else {
            ctx.lineTo(x, y);
        }
    });

    ctx.stroke();

    // Draw starting line
    ctx.strokeStyle = 'rgba(255,215,0,0.5)';
    ctx.setLineDash([5, 5]);
    const startY = height - padding - ((1000 - minY) / range) * (height - 2 * padding);
    ctx.beginPath();
    ctx.moveTo(padding, startY);
    ctx.lineTo(width - padding, startY);
    ctx.stroke();
    ctx.setLineDash([]);

    // Labels
    ctx.fillStyle = 'white';
    ctx.font = '12px sans-serif';
    ctx.textAlign = 'right';
    ctx.fillText(`$${maxY.toFixed(0)}`, padding - 5, padding + 5);
    ctx.fillText(`$${minY.toFixed(0)}`, padding - 5, height - padding);
    ctx.textAlign = 'center';
    ctx.fillText('Hands Played', width / 2, height - 5);
}

function renderDrillChart(stats) {
    const canvas = document.getElementById('drill-chart');
    if (!canvas) return;

    const ctx = canvas.getContext('2d');
    const width = canvas.width;
    const height = canvas.height;
    const padding = 40;

    // Clear canvas
    ctx.clearRect(0, 0, width, height);

    const drills = [
        { name: 'Count', correct: stats.count_drills_correct, total: stats.count_drills_attempted },
        { name: 'Strategy', correct: stats.strategy_drills_correct, total: stats.strategy_drills_attempted },
        { name: 'Deviations', correct: stats.deviation_drills_correct, total: stats.deviation_drills_attempted },
        { name: 'Speed', correct: stats.speed_drills_correct, total: stats.speed_drills_attempted },
    ];

    const barWidth = (width - 2 * padding) / drills.length - 20;
    const maxHeight = height - 2 * padding;

    drills.forEach((drill, i) => {
        const x = padding + 10 + i * (barWidth + 20);
        const accuracy = drill.total > 0 ? drill.correct / drill.total : 0;
        const barHeight = accuracy * maxHeight;

        // Background bar
        ctx.fillStyle = 'rgba(255,255,255,0.1)';
        ctx.fillRect(x, padding, barWidth, maxHeight);

        // Accuracy bar
        ctx.fillStyle = accuracy >= 0.8 ? '#28a745' : (accuracy >= 0.6 ? '#fd7e14' : '#dc3545');
        ctx.fillRect(x, padding + maxHeight - barHeight, barWidth, barHeight);

        // Label
        ctx.fillStyle = 'white';
        ctx.font = '12px sans-serif';
        ctx.textAlign = 'center';
        ctx.fillText(drill.name, x + barWidth / 2, height - 5);

        // Percentage
        if (drill.total > 0) {
            ctx.fillText(`${(accuracy * 100).toFixed(0)}%`, x + barWidth / 2, padding + maxHeight - barHeight - 5);
        } else {
            ctx.fillStyle = 'rgba(255,255,255,0.5)';
            ctx.fillText('N/A', x + barWidth / 2, padding + maxHeight / 2);
        }
    });
}
