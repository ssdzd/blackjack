/**
 * Counting drill and speed-counting drill
 */

import { apiPost, getSessionId } from '../api.js';
import { renderCard } from '../components/cards.js';
import { refreshProfile } from '../progression.js';

let currentDrill = null;
let drillCardIndex = 0;
let drillInterval = null;
let drillSpeed = 1500; // ms between cards
let speedModeEnabled = false;
let speedDrillStartTime = null;
let speedTimerInterval = null;
let highScores = JSON.parse(localStorage.getItem('speedDrillHighScores') || '[]');

export function initDrills() {
    document.getElementById('btn-start-drill')?.addEventListener('click', startCountingDrill);
    document.getElementById('btn-submit-count')?.addEventListener('click', submitCount);
    document.getElementById('speed-mode')?.addEventListener('change', toggleSpeedMode);
}

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

    const endpoint = speedModeEnabled
        ? '/api/training/counting/speed-drill'
        : '/api/training/counting/drill';

    const body = speedModeEnabled
        ? { num_cards: numCards, system: system, card_speed_ms: drillSpeed }
        : { num_cards: numCards, system: system };

    try {
        currentDrill = await apiPost(endpoint, body);
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

    if (speedModeEnabled) {
        updateCardProgress(drillCardIndex, currentDrill.cards.length);
    }
}

async function submitCount() {
    const userCount = parseFloat(document.getElementById('user-count').value);

    // Stop timer for speed mode
    stopSpeedTimer();
    const completionTime = speedModeEnabled ? Date.now() - speedDrillStartTime : 0;

    if (speedModeEnabled && currentDrill.drill_id) {
        try {
            const result = await apiPost('/api/training/counting/speed-drill/verify', {
                drill_id: currentDrill.drill_id,
                user_count: userCount,
                completion_time_ms: completionTime
            });

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

                saveHighScore(result.score, result.completion_time_ms, currentDrill.num_cards);
                refreshProfile({ celebrate: true });
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
            const result = await apiPost('/api/training/counting/verify', {
                session_id: getSessionId(),
                user_count: userCount
            });

            const resultEl = document.getElementById('drill-result');
            resultEl.classList.remove('hidden');

            if (result.correct) {
                resultEl.innerHTML = `<span class="correct">Correct!</span> Count: ${result.actual_count}`;
            } else {
                resultEl.innerHTML = `<span class="incorrect">Incorrect.</span> Your answer: ${userCount}, Actual: ${result.actual_count}`;
            }
            refreshProfile({ celebrate: true });

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
