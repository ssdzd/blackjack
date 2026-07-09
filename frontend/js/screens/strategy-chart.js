/**
 * Basic strategy reference chart modal with live-hand highlighting
 */

import { appState } from '../state.js';
import { STRATEGY_TABLES, getActionClass } from '../strategy-data.js';
import { getHandInfo } from '../hand-info.js';

export function initStrategyChart() {
    document.getElementById('btn-strategy-chart')?.addEventListener('click', openStrategyChart);
    document.querySelector('#strategy-chart-modal .modal-close')?.addEventListener('click', closeStrategyChart);
    setupChartTabs();

    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape') {
            closeStrategyChart();
            return;
        }
        if (e.key.toLowerCase() === 'c' && document.activeElement.tagName !== 'INPUT') {
            const modal = document.getElementById('strategy-chart-modal');
            if (modal?.classList.contains('hidden')) {
                openStrategyChart();
            } else {
                closeStrategyChart();
            }
        }
    });

    // Click outside modal to close
    document.addEventListener('click', (e) => {
        const modal = document.getElementById('strategy-chart-modal');
        if (!modal || modal.classList.contains('hidden')) return;
        if (e.target === modal) {
            closeStrategyChart();
        }
    });
}

export function openStrategyChart() {
    const modal = document.getElementById('strategy-chart-modal');
    if (!modal) return;

    generateStrategyCharts();
    modal.classList.remove('hidden');

    if (appState.gameState?.state === 'PLAYER_TURN') {
        highlightCurrentHand();
    }
}

export function closeStrategyChart() {
    const modal = document.getElementById('strategy-chart-modal');
    if (modal) {
        modal.classList.add('hidden');
    }
}

/**
 * Re-apply the highlight when the game state changes while the modal is open
 */
export function refreshChartHighlight() {
    if (!document.getElementById('strategy-chart-modal')?.classList.contains('hidden')) {
        highlightCurrentHand();
    }
}

function generateStrategyCharts() {
    generateChart('hard', [8, 9, 10, 11, 12, 13, 14, 15, 16, 17], total => `${total}`);
    generateChart('soft', [13, 14, 15, 16, 17, 18, 19, 20], total => `A,${total - 11}`);
    generateChart('pairs', [2, 3, 4, 5, 6, 7, 8, 9, 10, 11], rank => rank === 11 ? 'A,A' : `${rank},${rank}`);
}

function generateChart(type, playerKeys, rowLabel) {
    const container = document.getElementById(`chart-${type}`);
    if (!container) return;

    const dealerCards = [2, 3, 4, 5, 6, 7, 8, 9, 10, 11];
    container.style.gridTemplateColumns = `repeat(${dealerCards.length + 1}, 1fr)`;

    let html = '<div class="chart-cell chart-header"></div>';
    dealerCards.forEach(d => {
        html += `<div class="chart-cell chart-header">${d === 11 ? 'A' : d}</div>`;
    });

    playerKeys.forEach(key => {
        html += `<div class="chart-cell chart-row-header">${rowLabel(key)}</div>`;
        dealerCards.forEach(dealer => {
            const action = STRATEGY_TABLES[type][key]?.[dealer] || 'H';
            const actionClass = getActionClass(action);
            html += `<div class="chart-cell ${actionClass}" data-player="${key}" data-dealer="${dealer}" data-type="${type}">${action}</div>`;
        });
    });

    container.innerHTML = html;
}

function setupChartTabs() {
    const tabs = document.querySelectorAll('.chart-tab');
    tabs.forEach(tab => {
        tab.addEventListener('click', () => {
            const tabName = tab.dataset.tab;

            tabs.forEach(t => t.classList.remove('active'));
            tab.classList.add('active');

            document.querySelectorAll('.chart-grid').forEach(grid => grid.classList.add('hidden'));
            document.getElementById(`chart-${tabName}`)?.classList.remove('hidden');

            if (appState.gameState?.state === 'PLAYER_TURN') {
                highlightCurrentHand();
            }
        });
    });
}

function highlightCurrentHand() {
    document.querySelectorAll('.chart-cell.highlighted').forEach(cell => {
        cell.classList.remove('highlighted');
    });

    const state = appState.gameState;
    if (!state || state.state !== 'PLAYER_TURN') return;

    const handInfo = getHandInfo(state);
    if (!handInfo) return;

    const { playerValue, dealerUpcard, isPair, isSoft, pairRank } = handInfo;

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
