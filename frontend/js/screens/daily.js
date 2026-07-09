/**
 * Daily challenge screen: intro card, live run banner, count check-ins,
 * result modal with shareable card.
 */

import { apiGet } from '../api.js';
import { switchMode } from '../nav.js';
import { getProfileId } from '../progression.js';
import { onDaily, startDailyRun, sendCountCheckin } from './table.js';
import { downloadShareCard } from '../components/share-card.js';
import { toast } from '../juice/toast.js';
import { play } from '../juice/sound.js';
import { burstAt } from '../juice/particles.js';

let lastResult = null;

export function initDaily() {
    document.getElementById('btn-start-daily')?.addEventListener('click', () => {
        switchMode('play');
        startDailyRun();
    });

    document.getElementById('btn-checkin-submit')?.addEventListener('click', submitCheckin);
    document.getElementById('checkin-input')?.addEventListener('keydown', (e) => {
        if (e.key === 'Enter') submitCheckin();
    });

    document.getElementById('btn-daily-copy')?.addEventListener('click', async () => {
        if (!lastResult) return;
        try {
            await navigator.clipboard.writeText(lastResult.share_text);
            toast('Result copied — paste it anywhere', { variant: 'gold' });
        } catch {
            toast('Could not access the clipboard', { variant: 'danger' });
        }
    });

    document.getElementById('btn-daily-card')?.addEventListener('click', () => {
        if (lastResult) downloadShareCard(lastResult);
    });

    document.getElementById('btn-daily-close')?.addEventListener('click', () => {
        document.getElementById('daily-result-modal')?.classList.add('hidden');
        switchMode('daily');
        showDaily();
    });

    onDaily(handleDailyMessage);
}

export async function showDaily() {
    const profileId = getProfileId();
    const meta = await apiGet(
        `/api/progression/daily${profileId ? `?profile_id=${profileId}` : ''}`
    );

    document.getElementById('daily-number').textContent = `#${meta.number}`;
    document.getElementById('daily-date').textContent = meta.date;
    document.getElementById('daily-rules').textContent = meta.rules_summary;
    document.getElementById('daily-format').textContent =
        `${meta.rounds} rounds · bets $${meta.min_bet}–$${meta.max_bet} · count hidden · ${meta.checkin_rounds.length} check-ins`;

    const startBtn = document.getElementById('btn-start-daily');
    const attempted = document.getElementById('daily-attempted');

    if (meta.attempted && meta.result) {
        startBtn.classList.add('hidden');
        attempted.classList.remove('hidden');
        attempted.querySelector('.daily-best-score').textContent =
            `${meta.result.score}/1000 (${meta.result.grade})`;
    } else {
        startBtn.classList.remove('hidden');
        attempted.classList.add('hidden');
    }
}

function handleDailyMessage(type, data) {
    if (type === 'daily_started') {
        const banner = document.getElementById('daily-banner');
        banner.classList.remove('hidden');
        banner.textContent = `DAILY #${data.number} · ROUND 1/${data.rounds}`;
        toast(`Bets $${data.min_bet}–$${data.max_bet}. The count is hidden — keep it in your head.`, {
            title: `Daily #${data.number}`,
            variant: 'gold',
            duration: 4200,
        });
    }

    if (type === 'daily_progress') {
        const banner = document.getElementById('daily-banner');
        const next = Math.min(data.round + 1, data.rounds);
        banner.textContent = `DAILY · ROUND ${next}/${data.rounds}`;
        if (data.round >= data.rounds) {
            banner.textContent = 'DAILY · FINAL COUNT';
        }
    }

    if (type === 'count_checkin_request') {
        const modal = document.getElementById('checkin-modal');
        modal.classList.remove('hidden');
        const input = document.getElementById('checkin-input');
        input.value = '';
        input.focus();
        play('flip');
    }

    if (type === 'count_checkin_result') {
        // Only surface during a visible checkin modal flow
        const modal = document.getElementById('checkin-modal');
        if (!modal.classList.contains('hidden')) {
            modal.classList.add('hidden');
            if (data.correct) {
                toast('Exact. The count is real.', { variant: 'gold', title: 'Count check' });
            } else {
                toast(`You said ${data.answer}, the count was ${data.actual}.`, {
                    variant: 'danger',
                    title: 'Count check',
                    duration: 3800,
                });
            }
        }
    }

    if (type === 'daily_complete') {
        lastResult = data;
        showResultModal(data);
    }
}

function submitCheckin() {
    const input = document.getElementById('checkin-input');
    const value = parseFloat(input.value);
    if (Number.isNaN(value)) return;
    sendCountCheckin(value);
}

function showResultModal(result) {
    const modal = document.getElementById('daily-result-modal');
    modal.querySelector('.daily-score-big').textContent = result.score;
    modal.querySelector('.daily-grade-seal').textContent = result.grade;
    modal.querySelector('.daily-breakdown').textContent =
        `Decisions ${Math.round(result.decisions_pct)}% · Counts ${Math.round(result.counts_pct)}% · ` +
        `${result.net > 0 ? '+' : ''}${Math.round(result.net)} units`;
    modal.querySelector('.daily-grid').textContent = result.emoji_grid;

    document.getElementById('daily-banner')?.classList.add('hidden');
    modal.classList.remove('hidden');
    play(result.score >= 700 ? 'blackjack' : 'win');
    burstAt(modal.querySelector('.daily-score-big'), 'confetti', { count: 50 });
}
