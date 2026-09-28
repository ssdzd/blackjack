/**
 * Settings panel: counting system, count visibility, table rules, sound.
 *
 * Game-affecting choices go to the server over the WebSocket configure
 * message; presentation choices persist locally.
 */

import { configureSession } from './table.js';
import { isMuted, setMuted } from '../juice/sound.js';
import { toast } from '../juice/toast.js';
import { openModal, closeModal, bindBackdropClose } from '../modal.js';

const LS_KEY = 'bjt-settings';

export function loadSettings() {
    try {
        return JSON.parse(localStorage.getItem(LS_KEY) || '{}');
    } catch {
        return {};
    }
}

function saveSettings(patch) {
    const merged = { ...loadSettings(), ...patch };
    localStorage.setItem(LS_KEY, JSON.stringify(merged));
    return merged;
}

export function initSettings() {
    const panel = document.getElementById('settings-panel');
    if (!panel) return;

    const saved = loadSettings();

    const systemSel = document.getElementById('setting-system');
    const visibilitySel = document.getElementById('setting-visibility');
    const rulesSel = document.getElementById('setting-rules');
    const soundChk = document.getElementById('setting-sound');

    if (saved.counting_system && systemSel) systemSel.value = saved.counting_system;
    if (saved.visibility && visibilitySel) visibilitySel.value = saved.visibility;
    if (saved.rules_preset && rulesSel) rulesSel.value = saved.rules_preset;
    if (soundChk) soundChk.checked = !isMuted();

    // Re-apply persisted game settings to the (possibly fresh) server session
    if (saved.counting_system || saved.visibility) {
        configureSession({
            counting_system: saved.counting_system,
            visibility: saved.visibility,
        });
    }

    systemSel?.addEventListener('change', () => {
        saveSettings({ counting_system: systemSel.value });
        configureSession({ counting_system: systemSel.value });
        toast(`Counting system: ${systemSel.options[systemSel.selectedIndex].text}. Count resets.`, { variant: 'gold' });
    });

    visibilitySel?.addEventListener('change', () => {
        saveSettings({ visibility: visibilitySel.value });
        configureSession({ visibility: visibilitySel.value });
    });

    rulesSel?.addEventListener('change', () => {
        saveSettings({ rules_preset: rulesSel.value });
        configureSession({ rules_preset: rulesSel.value });
        toast('Table rules changed — new shoe, fresh bankroll.', { variant: 'gold' });
    });

    soundChk?.addEventListener('change', () => {
        setMuted(!soundChk.checked);
        const muteBtn = document.getElementById('btn-mute');
        if (muteBtn) muteBtn.textContent = soundChk.checked ? 'Sound: On' : 'Sound: Off';
    });

    document.getElementById('settings-close')?.addEventListener('click', () => {
        closeModal(panel);
    });
    bindBackdropClose(panel);
}

/** Toggle the settings panel, keeping focus trap/return in sync. */
export function toggleSettings() {
    const panel = document.getElementById('settings-panel');
    if (!panel) return;
    if (panel.classList.contains('hidden')) {
        openModal(panel);
    } else {
        closeModal(panel);
    }
}
