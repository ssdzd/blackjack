/**
 * Basic-strategy drill and deviation-focused drill
 */

import { apiPost } from '../api.js';
import { renderCard } from '../components/cards.js';

let currentStrategyDrill = null;
let deviationFocusMode = false;

export function initStrategyDrill() {
    document.getElementById('btn-start-strategy')?.addEventListener('click', startStrategyDrill);
    document.getElementById('include-deviations')?.addEventListener('change', toggleDeviationSettings);
    document.getElementById('deviation-focus-mode')?.addEventListener('change', toggleDeviationFocus);

    document.querySelectorAll('.strategy-action-btn').forEach(btn => {
        btn.addEventListener('click', () => checkStrategyAction(btn.dataset.action));
    });
}

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
        const tcMin = parseFloat(document.getElementById('tc-range-min')?.value || -5);
        const tcMax = parseFloat(document.getElementById('tc-range-max')?.value || 10);

        try {
            currentStrategyDrill = await apiPost('/api/training/strategy/deviation-drill', {
                true_count_range_min: tcMin,
                true_count_range_max: tcMax,
                include_fab4: true
            });
            currentStrategyDrill.is_deviation_drill = true;

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
        const trueCount = includeDeviations ? parseFloat(document.getElementById('drill-true-count')?.value || 0) : null;

        try {
            currentStrategyDrill = await apiPost('/api/training/strategy/drill', {
                include_deviations: includeDeviations,
                true_count: trueCount
            });
            currentStrategyDrill.is_deviation_drill = false;

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
