/**
 * App entry: screen routing, panel chrome, and screen initialization
 */

import { appState } from './state.js';
import { onEnter, switchMode } from './nav.js';
import { initTable, statsTracker, resetGame, revealCount, configureSession } from './screens/table.js';
import { initStrategyChart } from './screens/strategy-chart.js';
import { initDrills } from './screens/drills.js';
import { initStrategyDrill } from './screens/strategy-drill.js';
import { initPerformance, refreshPerformanceStats } from './screens/performance.js';
import { initSettings } from './screens/settings.js';
import { initProfile, showProfile } from './screens/profile.js';
import { initDaily, showDaily } from './screens/daily.js';
import { ensureProfile } from './progression.js';
import { armSound, isMuted, setMuted } from './juice/sound.js';

function setupNavigation() {
    const routes = ['play', 'count-drill', 'strategy-drill', 'daily', 'performance', 'profile'];
    for (const mode of routes) {
        document.getElementById(`nav-${mode}`)?.addEventListener('click', (e) => {
            e.preventDefault();
            switchMode(mode);
        });
    }

    onEnter('performance', refreshPerformanceStats);
    onEnter('profile', showProfile);
    onEnter('daily', showDaily);

    document.getElementById('nav-settings')?.addEventListener('click', (e) => {
        e.preventDefault();
        document.getElementById('settings-panel')?.classList.toggle('hidden');
    });
}

function setupCountToggle() {
    const toggleBtn = document.getElementById('toggle-count');
    let countVisible = true;
    if (toggleBtn) {
        toggleBtn.addEventListener('click', () => {
            countVisible = !countVisible;
            document.getElementById('count-section').classList.toggle('blurred', !countVisible);
            toggleBtn.textContent = countVisible ? 'Hide Count' : 'Show Count';
        });
    }
}

function setupMuteButton() {
    const btn = document.getElementById('btn-mute');
    if (!btn) return;
    const label = () => {
        btn.textContent = isMuted() ? 'Sound: Off' : 'Sound: On';
    };
    label();
    btn.addEventListener('click', () => {
        setMuted(!isMuted());
        label();
    });
}

function init() {
    armSound();

    initTable();
    initStrategyChart();
    initDrills();
    initStrategyDrill();
    initPerformance();
    initSettings();
    initProfile();
    initDaily();

    setupNavigation();
    setupCountToggle();
    setupMuteButton();

    document.getElementById('btn-reset-session')?.addEventListener('click', resetGame);
    document.getElementById('btn-reveal-count')?.addEventListener('click', revealCount);

    // Attach the player profile to the live game session
    ensureProfile()
        .then(profile => configureSession({ profile_id: profile.profile_id }))
        .catch(err => console.error('Profile init failed:', err));
}

init();

// Expose a few pieces for debugging in the console
window.__bjt = { appState, statsTracker };
