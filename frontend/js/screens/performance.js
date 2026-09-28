/**
 * Performance tracking screen
 */

import { getSessionId } from '../api.js';
import { renderBankrollChart, renderDrillChart } from '../components/charts.js';

export function initPerformance() {
    document.getElementById('btn-refresh-stats')?.addEventListener('click', refreshPerformanceStats);
    document.getElementById('btn-reset-stats')?.addEventListener('click', resetPerformanceStats);
}

export async function refreshPerformanceStats() {
    try {
        const response = await fetch(`/api/stats/performance/${getSessionId()}`);
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
        const response = await fetch(`/api/stats/performance/${getSessionId()}`, {
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
