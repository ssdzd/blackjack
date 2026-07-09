/**
 * App entry: screen routing, panel chrome, and screen initialization
 */

import { appState } from './state.js';
import { initTable, statsTracker, resetGame, revealCount, configureSession } from './screens/table.js';
import { initStrategyChart } from './screens/strategy-chart.js';
import { initDrills } from './screens/drills.js';
import { initStrategyDrill } from './screens/strategy-drill.js';
import { initPerformance, refreshPerformanceStats } from './screens/performance.js';
import { initSettings } from './screens/settings.js';
import { initProfile, showProfile } from './screens/profile.js';
import { ensureProfile } from './progression.js';
import { armSound, isMuted, setMuted } from './juice/sound.js';

function setupNavigation() {
    document.getElementById('nav-play').addEventListener('click', (e) => {
        e.preventDefault();
        switchMode('play');
    });

    document.getElementById('nav-count-drill').addEventListener('click', (e) => {
        e.preventDefault();
        switchMode('count-drill');
    });

    document.getElementById('nav-strategy-drill').addEventListener('click', (e) => {
        e.preventDefault();
        switchMode('strategy-drill');
    });

    document.getElementById('nav-performance')?.addEventListener('click', (e) => {
        e.preventDefault();
        switchMode('performance');
        refreshPerformanceStats();
    });

    document.getElementById('nav-profile')?.addEventListener('click', (e) => {
        e.preventDefault();
        switchMode('profile');
        showProfile();
    });

    document.getElementById('nav-settings')?.addEventListener('click', (e) => {
        e.preventDefault();
        toggleSettings();
    });
}

function switchMode(mode) {
    appState.mode = mode;

    // Update nav active states
    document.querySelectorAll('footer nav a').forEach(a => a.classList.remove('active'));
    document.getElementById(`nav-${mode === 'play' ? 'play' : mode}`).classList.add('active');

    // Show/hide sections
    document.getElementById('game-area').classList.toggle('hidden', mode !== 'play');
    document.getElementById('count-drill-area')?.classList.toggle('hidden', mode !== 'count-drill');
    document.getElementById('strategy-drill-area')?.classList.toggle('hidden', mode !== 'strategy-drill');
    document.getElementById('performance-area')?.classList.toggle('hidden', mode !== 'performance');
    document.getElementById('profile-area')?.classList.toggle('hidden', mode !== 'profile');
}

function toggleSettings() {
    const settingsPanel = document.getElementById('settings-panel');
    if (settingsPanel) {
        settingsPanel.classList.toggle('hidden');
    }
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
