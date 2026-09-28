/**
 * Hand-rolled canvas charts for the performance screen
 */

export function renderBankrollChart(history) {
    const canvas = document.getElementById('bankroll-chart');
    if (!canvas) return;

    const ctx = canvas.getContext('2d');
    const width = canvas.width;
    const height = canvas.height;
    const padding = 40;

    ctx.clearRect(0, 0, width, height);

    if (!history || history.length === 0) {
        ctx.fillStyle = 'rgba(255,255,255,0.5)';
        ctx.textAlign = 'center';
        ctx.fillText('No data yet. Play some hands to see your bankroll history!', width / 2, height / 2);
        return;
    }

    // Filter for hand results only
    const handHistory = history.filter(h =>
        ['hand_win', 'hand_loss', 'hand_push', 'hand_blackjack'].includes(h.event_type)
    );

    if (handHistory.length === 0) {
        ctx.fillStyle = 'rgba(255,255,255,0.5)';
        ctx.textAlign = 'center';
        ctx.fillText('No hand history yet.', width / 2, height / 2);
        return;
    }

    // Calculate running bankroll
    const points = [];
    let bankroll = 1000;
    handHistory.forEach((h, i) => {
        bankroll = h.bankroll + 1000; // Approximate
        points.push({ x: i, y: bankroll });
    });

    const minY = Math.min(...points.map(p => p.y), 0);
    const maxY = Math.max(...points.map(p => p.y), 1000);
    const range = maxY - minY || 1;

    // Draw axes
    ctx.strokeStyle = 'rgba(255,255,255,0.3)';
    ctx.beginPath();
    ctx.moveTo(padding, padding);
    ctx.lineTo(padding, height - padding);
    ctx.lineTo(width - padding, height - padding);
    ctx.stroke();

    // Draw line
    ctx.strokeStyle = points[points.length - 1].y >= 1000 ? '#28a745' : '#dc3545';
    ctx.lineWidth = 2;
    ctx.beginPath();

    points.forEach((p, i) => {
        const x = padding + (p.x / (points.length - 1 || 1)) * (width - 2 * padding);
        const y = height - padding - ((p.y - minY) / range) * (height - 2 * padding);

        if (i === 0) {
            ctx.moveTo(x, y);
        } else {
            ctx.lineTo(x, y);
        }
    });

    ctx.stroke();

    // Draw starting line
    ctx.strokeStyle = 'rgba(255,215,0,0.5)';
    ctx.setLineDash([5, 5]);
    const startY = height - padding - ((1000 - minY) / range) * (height - 2 * padding);
    ctx.beginPath();
    ctx.moveTo(padding, startY);
    ctx.lineTo(width - padding, startY);
    ctx.stroke();
    ctx.setLineDash([]);

    // Labels
    ctx.fillStyle = 'white';
    ctx.font = '12px sans-serif';
    ctx.textAlign = 'right';
    ctx.fillText(`$${maxY.toFixed(0)}`, padding - 5, padding + 5);
    ctx.fillText(`$${minY.toFixed(0)}`, padding - 5, height - padding);
    ctx.textAlign = 'center';
    ctx.fillText('Hands Played', width / 2, height - 5);
}

export function renderDrillChart(stats) {
    const canvas = document.getElementById('drill-chart');
    if (!canvas) return;

    const ctx = canvas.getContext('2d');
    const width = canvas.width;
    const height = canvas.height;
    const padding = 40;

    ctx.clearRect(0, 0, width, height);

    const drills = [
        { name: 'Count', correct: stats.count_drills_correct, total: stats.count_drills_attempted },
        { name: 'Strategy', correct: stats.strategy_drills_correct, total: stats.strategy_drills_attempted },
        { name: 'Deviations', correct: stats.deviation_drills_correct, total: stats.deviation_drills_attempted },
        { name: 'Speed', correct: stats.speed_drills_correct, total: stats.speed_drills_attempted },
    ];

    const barWidth = (width - 2 * padding) / drills.length - 20;
    const maxHeight = height - 2 * padding;

    drills.forEach((drill, i) => {
        const x = padding + 10 + i * (barWidth + 20);
        const accuracy = drill.total > 0 ? drill.correct / drill.total : 0;
        const barHeight = accuracy * maxHeight;

        // Background bar
        ctx.fillStyle = 'rgba(255,255,255,0.1)';
        ctx.fillRect(x, padding, barWidth, maxHeight);

        // Accuracy bar
        ctx.fillStyle = accuracy >= 0.8 ? '#28a745' : (accuracy >= 0.6 ? '#fd7e14' : '#dc3545');
        ctx.fillRect(x, padding + maxHeight - barHeight, barWidth, barHeight);

        // Label
        ctx.fillStyle = 'white';
        ctx.font = '12px sans-serif';
        ctx.textAlign = 'center';
        ctx.fillText(drill.name, x + barWidth / 2, height - 5);

        // Percentage
        if (drill.total > 0) {
            ctx.fillText(`${(accuracy * 100).toFixed(0)}%`, x + barWidth / 2, padding + maxHeight - barHeight - 5);
        } else {
            ctx.fillStyle = 'rgba(255,255,255,0.5)';
            ctx.fillText('N/A', x + barWidth / 2, padding + maxHeight / 2);
        }
    });
}
