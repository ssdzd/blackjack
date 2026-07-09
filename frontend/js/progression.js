/**
 * Client-side progression glue: profile identity, XP bar, badge toasts.
 *
 * The server owns all progression math; this module keeps a cached copy,
 * renders the header XP chip, and celebrates deltas (XP crunch, badge
 * unlocks, level-ups, node masteries).
 */

import { apiGet, apiPost } from './api.js';
import { toast } from './juice/toast.js';
import { play } from './juice/sound.js';
import { burstAt } from './juice/particles.js';

let profile = null;
let badgeBook = null;

export function getProfileId() {
    return localStorage.getItem('profileId');
}

export function getCachedProfile() {
    return profile;
}

export async function ensureProfile() {
    let id = getProfileId();
    if (id) {
        profile = await apiGet(`/api/progression/profile/${id}`);
    } else {
        profile = await apiPost('/api/progression/profile');
        localStorage.setItem('profileId', profile.profile_id);
    }
    renderXpChip();
    return profile;
}

export async function refreshProfile({ celebrate = false } = {}) {
    const id = getProfileId();
    if (!id) return null;
    const before = profile;
    profile = await apiGet(`/api/progression/profile/${id}`);
    renderXpChip();
    if (celebrate && before) {
        const newBadges = Object.keys(profile.badges).filter(b => !(b in before.badges));
        for (const badgeId of newBadges) {
            await celebrateBadge(badgeId);
        }
        if (profile.level > before.level) {
            celebrateLevelUp(profile.level, profile.title);
        }
    }
    return profile;
}

async function badgeDef(badgeId) {
    if (!badgeBook) {
        const data = await apiGet('/api/progression/badges');
        badgeBook = Object.fromEntries(data.badges.map(b => [b.id, b]));
    }
    return badgeBook[badgeId] || { name: badgeId, flavor: '' };
}

async function celebrateBadge(badgeId) {
    const def = await badgeDef(badgeId);
    play('badge');
    toast(def.flavor, { title: `Badge — ${def.name}`, variant: 'gold', duration: 4200 });
    burstAt(document.getElementById('xp-chip'), 'confetti', { count: 26 });
}

function celebrateLevelUp(level, title) {
    play('blackjack');
    toast(`Level ${level} — ${title}`, { title: 'Level up', variant: 'gold', duration: 3600 });
    burstAt(document.getElementById('xp-chip'), 'sparks');
}

const NODE_NAMES = {}; // filled lazily by the skill-tree fetch when needed

/** Handle a live progression delta pushed over the WebSocket. */
export async function handleProgressionDelta(delta) {
    if (!delta) return;

    if (profile) {
        profile.xp = delta.xp_total;
        profile.level = delta.level;
        profile.title = delta.title;
    }
    renderXpChip(delta.xp_gained);

    for (const badgeId of delta.badges_awarded || []) {
        if (profile) profile.badges[badgeId] = Date.now() / 1000;
        await celebrateBadge(badgeId);
    }

    for (const [nodeId, status] of Object.entries(delta.node_changes || {})) {
        if (status === 'mastered') {
            play('badge');
            toast(`Skill mastered: ${NODE_NAMES[nodeId] || nodeId.replace(/-/g, ' ')}`, {
                title: 'Skill tree',
                variant: 'gold',
                duration: 3800,
            });
        }
    }

    if (delta.level_up) {
        celebrateLevelUp(delta.level, delta.title);
    }
}

// ---- XP chip in the header ----

function xpForLevel(level) {
    return level <= 1 ? 0 : Math.floor(100 * Math.pow(level - 1, 1.6));
}

export function renderXpChip(gained = 0) {
    const chip = document.getElementById('xp-chip');
    if (!chip || !profile) return;

    const current = xpForLevel(profile.level);
    const next = xpForLevel(profile.level + 1);
    const pct = Math.min(100, Math.round(((profile.xp - current) / (next - current)) * 100));

    chip.querySelector('.xp-level').textContent = `LV ${profile.level}`;
    chip.querySelector('.xp-title').textContent = profile.title;
    chip.querySelector('.xp-fill').style.width = `${pct}%`;
    chip.title = `${profile.xp} XP — ${next - profile.xp} to level ${profile.level + 1}`;

    if (gained > 0) {
        const pop = chip.querySelector('.xp-pop');
        pop.textContent = `+${gained}`;
        pop.classList.remove('xp-pop-anim');
        void pop.offsetWidth;
        pop.classList.add('xp-pop-anim');
    }
}
