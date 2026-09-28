/**
 * The Academy: the skill tree rendered as a stage-by-stage curriculum.
 *
 * Every node shows its gate ("PROVE IT: ...") and live progress from the
 * server; Train buttons route to the drill that feeds the node.
 */

import { apiGet } from '../api.js';
import { switchMode } from '../nav.js';
import { getProfileId } from '../progression.js';

const DRILL_ROUTES = {
    'strategy': 'strategy-drill',
    'deviation': 'strategy-drill',
    'counting': 'count-drill',
    'counting-adv': 'count-drill',
    'speed': 'count-drill',
    'tc-conversion': 'count-drill',
    'bet': 'play',
    'casino': 'play',
};

const DRILL_LABELS = {
    'strategy': 'Strategy drill',
    'deviation': 'Deviation drill',
    'counting': 'Counting drill',
    'counting-adv': 'Counting drill (Omega II / Wong)',
    'speed': 'Speed drill',
    'tc-conversion': 'TC converter',
    'bet': 'Play with betting hints off',
    'casino': 'Full shoe, count hidden',
};

export function initAcademy() {
    // rendered on show
}

export async function showAcademy() {
    const profileId = getProfileId();
    if (!profileId) return;
    const tree = await apiGet(`/api/progression/skill-tree/${profileId}`);
    render(tree.nodes);
}

function render(nodes) {
    const host = document.getElementById('academy-tree');
    if (!host) return;
    host.innerHTML = '';

    const byStage = new Map();
    for (const node of nodes) {
        if (!byStage.has(node.stage)) byStage.set(node.stage, []);
        byStage.get(node.stage).push(node);
    }

    for (const [stage, stageNodes] of [...byStage.entries()].sort((a, b) => a[0] - b[0])) {
        const stageEl = document.createElement('div');
        stageEl.className = 'academy-stage';
        stageEl.innerHTML = `<div class="stage-label">Stage ${stage}</div>`;

        const row = document.createElement('div');
        row.className = 'academy-row';

        for (const node of stageNodes) {
            const card = document.createElement('div');
            card.className = `node-card ${node.status}`;

            const pct = Math.round((node.progress || 0) * 100);
            card.innerHTML = `
                <div class="node-head">
                    <span class="node-name">${node.name}</span>
                    <span class="node-status">${statusLabel(node.status)}</span>
                </div>
                <div class="node-desc">${node.description}</div>
                <div class="node-gate">PROVE IT: ${node.gate}</div>
                ${node.status !== 'mastered' ? `
                    <div class="node-progress"><span style="width:${pct}%"></span></div>
                    <div class="node-progress-label">${pct}%${node.attempts ? ` · ${node.attempts} attempts` : ''}</div>
                ` : ''}
                ${node.unlocks.length ? `<div class="node-unlocks">Unlocks: ${node.unlocks.join(', ')}</div>` : ''}
                ${node.status !== 'locked' && node.status !== 'mastered'
                    ? `<button class="btn-small node-train">${DRILL_LABELS[node.drill_key] || 'Train'}</button>`
                    : ''}
            `;

            card.querySelector('.node-train')?.addEventListener('click', () => {
                const route = DRILL_ROUTES[node.drill_key] || 'play';
                switchMode(route);
                if (node.drill_key === 'tc-conversion') {
                    document.getElementById('tc-trainer')?.scrollIntoView({ block: 'center' });
                }
            });

            row.appendChild(card);
        }

        stageEl.appendChild(row);
        host.appendChild(stageEl);
    }
}

function statusLabel(status) {
    return {
        locked: 'LOCKED',
        available: 'READY',
        in_progress: 'IN PROGRESS',
        mastered: '★ MASTERED',
    }[status] || status;
}
