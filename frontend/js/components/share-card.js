/**
 * Canvas-rendered daily result card (1200x630) for download.
 *
 * Round squares are drawn as rects, not emoji glyphs, so the PNG renders
 * identically everywhere.
 */

const COLORS = {
    bg1: '#0d1210',
    bg2: '#142f22',
    gold: '#d4af37',
    goldBright: '#ecd489',
    ivory: '#f3ecdd',
    mute: '#a29b88',
    perfect: '#2c8a55',
    mixed: '#c8a02c',
    wrong: '#b3364a',
    none: '#3a4038',
};

export function renderShareCard(result) {
    const canvas = document.createElement('canvas');
    canvas.width = 1200;
    canvas.height = 630;
    const ctx = canvas.getContext('2d');

    // Room
    const bg = ctx.createRadialGradient(600, 140, 60, 600, 320, 900);
    bg.addColorStop(0, COLORS.bg2);
    bg.addColorStop(1, COLORS.bg1);
    ctx.fillStyle = bg;
    ctx.fillRect(0, 0, 1200, 630);

    // Gold frame
    ctx.strokeStyle = 'rgba(212, 175, 55, 0.5)';
    ctx.lineWidth = 2;
    ctx.strokeRect(26, 26, 1148, 578);
    ctx.strokeStyle = 'rgba(212, 175, 55, 0.18)';
    ctx.strokeRect(34, 34, 1132, 562);

    const serif = 'Georgia, "Times New Roman", serif';
    const mono = 'ui-monospace, "SF Mono", Consolas, monospace';

    // Header
    ctx.textAlign = 'center';
    ctx.fillStyle = COLORS.gold;
    ctx.font = `600 30px ${serif}`;
    ctx.fillText('♠  B L A C K J A C K   N O I R  ♦', 600, 92);

    ctx.fillStyle = COLORS.mute;
    ctx.font = `600 22px ${mono}`;
    ctx.fillText(`DAILY #${result.number} · ${result.date}`, 600, 132);

    // Score
    ctx.fillStyle = COLORS.goldBright;
    ctx.font = `700 130px ${serif}`;
    ctx.fillText(String(result.score), 560, 280);
    ctx.fillStyle = COLORS.mute;
    ctx.font = `500 34px ${serif}`;
    ctx.fillText('/1000', 720, 278);

    // Grade seal
    ctx.beginPath();
    ctx.arc(880, 240, 56, 0, Math.PI * 2);
    ctx.strokeStyle = COLORS.gold;
    ctx.lineWidth = 3;
    ctx.stroke();
    ctx.fillStyle = COLORS.goldBright;
    ctx.font = `700 64px ${serif}`;
    ctx.fillText(result.grade, 880, 262);

    // Breakdown line
    ctx.fillStyle = COLORS.ivory;
    ctx.font = `500 24px ${mono}`;
    const net = result.net > 0 ? `+${Math.round(result.net)}` : `${Math.round(result.net)}`;
    ctx.fillText(
        `Decisions ${Math.round(result.decisions_pct)}%   ·   Counts ${Math.round(result.counts_pct)}%   ·   ${net} units`,
        600, 350,
    );

    // Round grid: 20 squares, rows of 10
    const size = 40;
    const gap = 12;
    const cols = 10;
    const gridW = cols * size + (cols - 1) * gap;
    const startX = (1200 - gridW) / 2;
    const startY = 400;
    (result.round_results || []).slice(0, 20).forEach((r, i) => {
        const x = startX + (i % cols) * (size + gap);
        const y = startY + Math.floor(i / cols) * (size + gap);
        ctx.fillStyle = COLORS[r] || COLORS.none;
        ctx.beginPath();
        ctx.roundRect(x, y, size, size, 8);
        ctx.fill();
    });

    // Footer
    ctx.fillStyle = COLORS.mute;
    ctx.font = `500 18px ${mono}`;
    ctx.fillText('same shoe · every player · skill only', 600, 560);

    return canvas;
}

export function downloadShareCard(result) {
    const canvas = renderShareCard(result);
    const link = document.createElement('a');
    link.download = `blackjack-noir-daily-${result.number}.png`;
    link.href = canvas.toDataURL('image/png');
    link.click();
}
