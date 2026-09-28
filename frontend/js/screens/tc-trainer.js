/**
 * True-count converter trainer: RC + decks remaining -> integer TC.
 */

import { apiPost } from '../api.js';
import { refreshProfile } from '../progression.js';

let current = null;
let streak = 0;

export function initTcTrainer() {
    document.getElementById('btn-tc-new')?.addEventListener('click', newProblem);
    document.getElementById('btn-tc-submit')?.addEventListener('click', submit);
    document.getElementById('tc-answer')?.addEventListener('keydown', (e) => {
        if (e.key === 'Enter') submit();
    });
}

async function newProblem() {
    current = await apiPost('/api/training/tc-conversion');
    document.getElementById('tc-question').textContent =
        `RC ${current.running_count > 0 ? '+' : ''}${current.running_count} with ${current.decks_remaining} deck${current.decks_remaining === 1 ? '' : 's'} left`;
    const answer = document.getElementById('tc-answer');
    answer.value = '';
    answer.focus();
    document.getElementById('tc-result').textContent = '';
    document.getElementById('tc-result').className = '';
}

async function submit() {
    if (!current) return;
    const value = parseInt(document.getElementById('tc-answer').value, 10);
    if (Number.isNaN(value)) return;

    const result = await apiPost('/api/training/tc-conversion/verify', {
        drill_id: current.drill_id,
        user_tc: value,
    });
    current = null;

    const el = document.getElementById('tc-result');
    if (result.correct) {
        streak += 1;
        el.innerHTML = `<span class="correct">TC ${result.expected >= 0 ? '+' : ''}${result.expected}</span> (exact ${result.exact}) · streak ${streak}`;
    } else {
        streak = 0;
        el.innerHTML = `<span class="incorrect">TC is ${result.expected >= 0 ? '+' : ''}${result.expected}</span> (exact ${result.exact}). ${result.method_hint}`;
    }
    refreshProfile({ celebrate: true });

    // Keep the reps flowing
    setTimeout(newProblem, result.correct ? 700 : 2400);
}
