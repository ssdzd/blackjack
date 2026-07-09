/**
 * Career mode: the venue map, heat meter, back-offs, and advancement.
 */

import { apiGet } from '../api.js';
import { switchMode } from '../nav.js';
import { getProfileId } from '../progression.js';
import { onVenue, enterVenue, leaveVenue } from './table.js';
import { toast } from '../juice/toast.js';
import { play } from '../juice/sound.js';
import { addShake, SHAKE } from '../juice/shake.js';
import { burstAt } from '../juice/particles.js';

const NODE_LABELS = {
    'basic-strategy': 'Basic Strategy',
    'card-values': 'Card Values',
    'deck-countdown': 'Deck Countdown',
    'speed-counting': 'Speed Counting',
    'true-count': 'True Count',
    'betting-kelly': 'Kelly Betting',
    'illustrious-18': 'Illustrious 18',
    'fab-4': 'Fab Four',
    'casino-ready': 'Casino Ready',
};

export function initCareer() {
    onVenue(handleVenueMessage);
    document.getElementById('btn-leave-venue')?.addEventListener('click', () => {
        leaveVenue();
    });
}

export async function showCareer() {
    const profileId = getProfileId();
    if (!profileId) return;
    const data = await apiGet(`/api/progression/venues/${profileId}`);
    renderVenues(data.venues);
}

function renderVenues(venues) {
    const grid = document.getElementById('venue-grid');
    if (!grid) return;
    grid.innerHTML = '';

    for (const venue of venues) {
        const card = document.createElement('div');
        const state = venue.completed ? 'completed' : (venue.can_enter ? 'open' : 'locked');
        card.className = `venue-card ${state} ${venue.trap ? 'trap' : ''}`;

        const gates = venue.gates.map(g =>
            `<span class="gate ${g.met ? 'met' : 'unmet'}">${g.met ? '✓' : '✗'} ${NODE_LABELS[g.node] || g.node}</span>`
        ).join('');

        card.innerHTML = `
            <div class="venue-head">
                <span class="venue-name">${venue.name}</span>
                ${venue.completed ? '<span class="venue-ribbon">CLEARED</span>' : ''}
                ${venue.trap ? '<span class="venue-ribbon trap-ribbon">6:5</span>' : ''}
            </div>
            <div class="venue-flavor">${venue.flavor}</div>
            <div class="venue-stats">
                <span>${venue.rules_summary}</span>
                <span class="venue-edge ${venue.house_edge_pct > 1 ? 'bad' : ''}">house edge ${venue.house_edge_pct.toFixed(2)}%</span>
            </div>
            <div class="venue-stats">
                <span>buy-in $${venue.buy_in.toLocaleString()}</span>
                <span>${venue.target ? `clear at $${venue.target.toLocaleString()}` : 'no winning exit'}</span>
                <span>bets $${venue.min_bet}–$${venue.max_bet.toLocaleString()}</span>
            </div>
            ${gates ? `<div class="venue-gates">${gates}</div>` : ''}
            <button class="venue-enter" ${venue.can_enter ? '' : 'disabled'}>
                ${venue.completed ? 'Play Again' : (venue.trap ? 'Step Inside' : 'Take a Seat')}
            </button>
        `;

        card.querySelector('.venue-enter')?.addEventListener('click', () => {
            enterVenue(venue.id);
        });
        grid.appendChild(card);
    }
}

function setHeatMeter(value) {
    const meter = document.getElementById('heat-meter');
    if (!meter) return;
    meter.classList.remove('hidden');
    const fill = meter.querySelector('.heat-fill');
    fill.style.width = `${Math.min(value, 1) * 100}%`;
    meter.classList.toggle('heat-hot', value >= 0.65);
}

function handleVenueMessage(type, data) {
    const banner = document.getElementById('venue-banner');
    const leaveBtn = document.getElementById('btn-leave-venue');
    const meter = document.getElementById('heat-meter');

    if (type === 'venue_entered') {
        switchMode('play');
        banner.classList.remove('hidden');
        banner.textContent = data.target
            ? `${data.name.toUpperCase()} · CLEAR AT $${data.target.toLocaleString()}`
            : `${data.name.toUpperCase()} · HOUSE EDGE ${data.house_edge_pct.toFixed(2)}%`;
        leaveBtn.classList.remove('hidden');
        if (data.heat_tolerance > 0) {
            setHeatMeter(0);
        } else {
            meter.classList.add('hidden');
        }
        toast(data.trap
            ? 'Blackjack pays 6:5 here. Check the quant desk, then decide.'
            : `${data.rules_summary}. Bets $ up to your nerve.`, {
            title: data.name,
            variant: data.trap ? 'danger' : 'gold',
            duration: 4200,
        });
        play('chip');
    }

    if (type === 'heat') {
        setHeatMeter(data.heat);
        const worst = (data.events || []).filter(e => e.delta > 0).pop();
        if (worst && data.heat >= 0.4) {
            toast(worst.reason, { title: 'The pit is watching', variant: 'danger', duration: 3600 });
        }
    }

    if (type === 'backed_off') {
        addShake(SHAKE.IMPACT);
        play('bust');
        banner.classList.add('hidden');
        leaveBtn.classList.add('hidden');
        meter.classList.add('hidden');
        toast(data.lesson, {
            title: `Backed off — ${data.name}`,
            variant: 'danger',
            duration: 6000,
        });
        setTimeout(() => {
            switchMode('career');
            showCareer();
        }, 1200);
    }

    if (type === 'venue_complete') {
        play('blackjack');
        addShake(SHAKE.MEDIUM);
        burstAt(document.getElementById('player-hands'), 'confetti', { count: 60 });
        toast(`$${Math.round(data.bankroll).toLocaleString()} — the ${data.name} is cleared. The next room is open.`, {
            title: 'Venue cleared',
            variant: 'gold',
            duration: 5200,
        });
    }

    if (type === 'venue_bust') {
        banner.classList.add('hidden');
        leaveBtn.classList.add('hidden');
        meter.classList.add('hidden');
        toast(data.lesson, { title: `Busted out — ${data.name}`, variant: 'danger', duration: 5600 });
        setTimeout(() => {
            switchMode('career');
            showCareer();
        }, 1200);
    }

    if (type === 'trap_walkaway') {
        play('badge');
        toast(data.message, { title: 'Reads the fine print', variant: 'gold', duration: 5200 });
    }

    if (type === 'venue_left') {
        banner.classList.add('hidden');
        leaveBtn.classList.add('hidden');
        meter.classList.add('hidden');
    }
}
