/**
 * Profile screen: level, streak, badge case, lifetime numbers.
 */

import { apiGet } from '../api.js';
import { getProfileId, getCachedProfile, refreshProfile } from '../progression.js';

let badgeDefs = null;

export function initProfile() {
    // nothing to wire until first show
}

export async function showProfile() {
    const id = getProfileId();
    if (!id) return;

    const [profile, badges] = await Promise.all([
        refreshProfile(),
        badgeDefs ? Promise.resolve(badgeDefs) : apiGet('/api/progression/badges').then(d => d.badges),
    ]);
    badgeDefs = badges;
    if (!profile) return;

    renderIdentity(profile);
    renderBadges(profile, badges);
    renderLifetime(profile);
}

function renderIdentity(profile) {
    const levelEl = document.getElementById('profile-level');
    if (levelEl) levelEl.textContent = profile.level;
    const titleEl = document.getElementById('profile-title');
    if (titleEl) titleEl.textContent = profile.title;
    const xpEl = document.getElementById('profile-xp');
    if (xpEl) xpEl.textContent = `${profile.xp.toLocaleString()} XP`;

    const streakEl = document.getElementById('profile-streak');
    if (streakEl) {
        const current = profile.streak?.current || 0;
        const best = profile.streak?.best || 0;
        streakEl.textContent = current > 0
            ? `${current} day${current === 1 ? '' : 's'} (best ${best})`
            : '—';
    }
}

function renderBadges(profile, badges) {
    const grid = document.getElementById('badge-grid');
    if (!grid) return;

    grid.innerHTML = '';
    for (const def of badges) {
        const earned = def.id in (profile.badges || {});
        if (def.secret && !earned) continue;

        const card = document.createElement('div');
        card.className = `badge-card ${earned ? 'earned' : 'locked'}`;
        // Earned/locked is currently conveyed by opacity alone — add a
        // text label so it reads correctly without color/contrast cues.
        card.innerHTML = `
            <div class="badge-name">${def.name}</div>
            <div class="badge-flavor">${def.flavor}</div>
            <div class="badge-footer">
                <span class="badge-category">${def.category}</span>
                <span class="badge-state">${earned ? 'Earned' : 'Locked'}</span>
            </div>`;
        grid.appendChild(card);
    }
}

const LIFETIME_LABELS = [
    ['hands', 'Hands played'],
    ['decisions_correct', 'Correct decisions'],
    ['deviations_correct', 'Index plays hit'],
    ['checkins_exact', 'Exact count check-ins'],
    ['kelly_streak_best', 'Best Kelly streak'],
    ['deck_countdown_pass', 'Deck countdowns'],
    ['dailies_complete', 'Daily challenges'],
    ['shoes_complete', 'Shoes finished'],
];

function renderLifetime(profile) {
    const list = document.getElementById('lifetime-stats');
    if (!list) return;
    list.innerHTML = '';
    for (const [key, label] of LIFETIME_LABELS) {
        const value = profile.lifetime?.[key] || 0;
        const row = document.createElement('div');
        row.className = 'stat-row';
        row.innerHTML = `<span>${label}:</span><span>${value.toLocaleString()}</span>`;
        list.appendChild(row);
    }
}
