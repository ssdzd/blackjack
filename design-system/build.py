"""Build self-contained design-system preview cards from the app's CSS.

Each card in dist/ is a standalone HTML file with the app's stylesheets
inlined, headed by an @dsCard marker so claude.ai/design can index it.
Regenerate after changing frontend/css/*:

    python design-system/build.py
"""

from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CSS_DIR = ROOT / "frontend" / "css"
DIST = Path(__file__).resolve().parent / "dist"

CSS_FILES = ["tokens.css", "base.css", "table.css", "components.css", "effects.css"]

# Preview pages get panel-friendly framing instead of the app's 100vh shell
PREVIEW_OVERRIDES = """
body { min-height: auto; padding: 28px; }
body::before, body::after { display: none; }
.ds-stage { display: flex; flex-wrap: wrap; gap: 18px; align-items: flex-start; }
.ds-col { display: flex; flex-direction: column; gap: 14px; }
.ds-label {
    font-family: var(--font-body); font-size: 10px; font-weight: 700;
    letter-spacing: .22em; text-transform: uppercase; color: var(--ivory-mute);
    margin: 14px 0 6px;
}
.ds-swatch { width: 132px; border-radius: 10px; overflow: hidden;
    border: 1px solid var(--panel-hairline); }
.ds-swatch .chip { height: 64px; }
.ds-swatch .meta { padding: 8px 10px; background: var(--panel-solid);
    font-family: var(--font-mono); font-size: 10px; color: var(--ivory-mute); }
.ds-swatch .meta b { display: block; font-size: 11px; color: var(--ivory);
    font-weight: 600; margin-bottom: 2px; }
"""

CARDS = {
    "palette.html": {
        "group": "Foundations",
        "name": "Palette",
        "subtitle": "Noir surfaces, gold, ivory, card inks",
        "width": 940,
        "body": """
<div class="ds-label">Surfaces</div>
<div class="ds-stage">
  <div class="ds-swatch"><div class="chip" style="background:var(--room)"></div><div class="meta"><b>room</b>#0a0c0b</div></div>
  <div class="ds-swatch"><div class="chip" style="background:var(--felt-hi)"></div><div class="meta"><b>felt-hi</b>#1d3a2a</div></div>
  <div class="ds-swatch"><div class="chip" style="background:var(--felt-lo)"></div><div class="meta"><b>felt-lo</b>#0d2016</div></div>
  <div class="ds-swatch"><div class="chip" style="background:var(--rail)"></div><div class="meta"><b>rail</b>#221910</div></div>
  <div class="ds-swatch"><div class="chip" style="background:var(--panel-solid)"></div><div class="meta"><b>panel</b>#101412</div></div>
</div>
<div class="ds-label">Metals &amp; ink</div>
<div class="ds-stage">
  <div class="ds-swatch"><div class="chip" style="background:var(--gold)"></div><div class="meta"><b>gold</b>#d4af37</div></div>
  <div class="ds-swatch"><div class="chip" style="background:var(--gold-bright)"></div><div class="meta"><b>gold-bright</b>#ecd489</div></div>
  <div class="ds-swatch"><div class="chip" style="background:var(--gold-deep)"></div><div class="meta"><b>gold-deep</b>#96762a</div></div>
  <div class="ds-swatch"><div class="chip" style="background:var(--ivory)"></div><div class="meta"><b>ivory</b>#f3ecdd</div></div>
  <div class="ds-swatch"><div class="chip" style="background:var(--ivory-mute)"></div><div class="meta"><b>ivory-mute</b>#a29b88</div></div>
  <div class="ds-swatch"><div class="chip" style="background:var(--loss)"></div><div class="meta"><b>loss</b>#cf5f6d</div></div>
  <div class="ds-swatch"><div class="chip" style="background:var(--card-red)"></div><div class="meta"><b>card-red</b>#ae2438</div></div>
  <div class="ds-swatch"><div class="chip" style="background:var(--win-green)"></div><div class="meta"><b>win-green</b>#58a877</div></div>
</div>
""",
    },
    "typography.html": {
        "group": "Foundations",
        "name": "Typography",
        "subtitle": "Display serif, HUD mono, body sans",
        "width": 760,
        "body": """
<div class="ds-label">Display serif — headings, results, table copy</div>
<div style="font-family:var(--font-display);color:var(--ivory)">
  <div style="font-size:40px;font-weight:700;letter-spacing:.1em;text-transform:uppercase">Blackjack</div>
  <div style="font-size:26px;font-weight:600;letter-spacing:.14em;text-transform:uppercase">Won $150!</div>
  <div style="font-size:20px;font-style:italic;color:var(--gold-bright)">Shoe shuffled — the count begins again</div>
</div>
<div class="ds-label">HUD mono — every number in the app</div>
<div style="font-family:var(--font-mono);color:var(--ivory)">
  <div style="font-size:24px;color:var(--gold-bright)">RC +7 &nbsp; TC +2.3</div>
  <div style="font-size:14px">$1,240 &nbsp; 61.2% &nbsp; N0 18,400 &nbsp; RoR 4.8%</div>
</div>
<div class="ds-label">Body sans — UI copy</div>
<div style="font-size:14px;color:var(--ivory-soft);max-width:46ch">
  The running count tracks every card you've seen. Divide by decks
  remaining to get the true count before you size your bet.
</div>
""",
    },
    "playing-cards.html": {
        "group": "Table",
        "name": "Playing cards",
        "subtitle": "Faces, red suits, dealer hole card",
        "width": 620,
        "body": """
<div class="ds-stage" style="background:radial-gradient(120% 120% at 50% 0%, var(--felt-hi), var(--felt-lo)); padding: 28px; border-radius: 16px;">
  <div class="card"><span class="card-rank">A</span><span class="card-suit">♠</span></div>
  <div class="card red"><span class="card-rank">K</span><span class="card-suit">♥</span></div>
  <div class="card"><span class="card-rank">10</span><span class="card-suit">♣</span></div>
  <div class="card red"><span class="card-rank">7</span><span class="card-suit">♦</span></div>
  <div class="card face-down"><span>?</span></div>
</div>
""",
    },
    "buttons.html": {
        "group": "Components",
        "name": "Buttons",
        "subtitle": "Gold plaque primary, dark plaques, danger, pills",
        "width": 720,
        "body": """
<div class="ds-label">Primary (gold plaque)</div>
<div class="ds-stage">
  <button id="btn-bet">Place Bet (B)</button>
  <button id="btn-new-round">New Round (N)</button>
</div>
<div class="ds-label">Table actions</div>
<div class="ds-stage">
  <button>Hit (H)</button>
  <button>Stand (S)</button>
  <button>Double (D)</button>
  <button disabled>Split (P)</button>
  <button>Surrender (R)</button>
</div>
<div class="ds-label">Utility</div>
<div class="ds-stage">
  <button class="btn-small">Refresh Stats</button>
  <button class="btn-small btn-danger">Reset All Stats</button>
  <button class="toggle-btn">Hide</button>
</div>
""",
    },
    "hud-panel.html": {
        "group": "Components",
        "name": "Count panel",
        "subtitle": "Glass side panel with count + session stats",
        "width": 460,
        "body": """
<aside id="stats-panel" style="position:static">
  <div id="count-section">
    <h3>Count <button id="toggle-count" class="toggle-btn">Hide</button></h3>
    <div id="running-count">Running: <span>+7</span></div>
    <div id="true-count">True: <span>+2.3</span></div>
    <div id="cards-remaining">Cards: <span>154</span></div>
  </div>
  <h3>Session Stats</h3>
  <div id="hands-played">Hands: <span>42</span></div>
  <div id="win-rate">Win Rate: <span>47.6%</span></div>
  <div id="net-result">Net: <span style="color:var(--gold-bright)">+$180</span></div>
</aside>
""",
    },
    "fields.html": {
        "group": "Components",
        "name": "Fields",
        "subtitle": "Numeric inputs and selects, mono values",
        "width": 560,
        "body": """
<div class="ds-stage">
  <div class="ds-col">
    <label for="a">Bet amount</label>
    <input id="a" type="number" value="25">
  </div>
  <div class="ds-col">
    <label for="b">Counting system</label>
    <select id="b"><option>Hi-Lo</option><option>KO</option><option>Omega II</option><option>Wong Halves</option></select>
  </div>
</div>
""",
    },
    "strategy-chart.html": {
        "group": "Components",
        "name": "Strategy chart",
        "subtitle": "Action-coded grid with highlight state",
        "width": 700,
        "body": """
<div class="chart-grid" style="grid-template-columns:repeat(6,1fr);max-width:520px">
  <div class="chart-cell chart-header"></div>
  <div class="chart-cell chart-header">2</div><div class="chart-cell chart-header">3</div>
  <div class="chart-cell chart-header">4</div><div class="chart-cell chart-header">5</div><div class="chart-cell chart-header">6</div>
  <div class="chart-cell chart-row-header">11</div>
  <div class="chart-cell action-double">D</div><div class="chart-cell action-double">D</div>
  <div class="chart-cell action-double">D</div><div class="chart-cell action-double">D</div><div class="chart-cell action-double">D</div>
  <div class="chart-cell chart-row-header">12</div>
  <div class="chart-cell action-hit">H</div><div class="chart-cell action-hit">H</div>
  <div class="chart-cell action-stand highlighted">S</div><div class="chart-cell action-stand">S</div><div class="chart-cell action-stand">S</div>
  <div class="chart-cell chart-row-header">16</div>
  <div class="chart-cell action-stand">S</div><div class="chart-cell action-stand">S</div>
  <div class="chart-cell action-stand">S</div><div class="chart-cell action-stand">S</div><div class="chart-cell action-surrender">R</div>
</div>
<div class="chart-legend" style="margin-top:12px">
  <span class="legend-item legend-hit">H = Hit</span>
  <span class="legend-item legend-stand">S = Stand</span>
  <span class="legend-item legend-double">D = Double</span>
  <span class="legend-item legend-split">P = Split</span>
  <span class="legend-item legend-surrender">R = Surrender</span>
</div>
""",
    },
    "table-scene.html": {
        "group": "Table",
        "name": "Table scene",
        "subtitle": "Felt, rail, hands, betting hint, gold CTA",
        "width": 1080,
        "body": """
<div id="game-area" style="min-height:600px;display:flex">
<div id="table-felt">
  <div id="game-message" class="visible">Blackjack!</div>
  <div id="dealer-area">
    <h2>Dealer</h2>
    <div class="cards">
      <div class="card"><span class="card-rank">10</span><span class="card-suit">♠</span></div>
      <div class="card face-down"><span>?</span></div>
    </div>
    <div class="hand-value">Showing: 10</div>
  </div>
  <div id="player-area">
    <h2>Player</h2>
    <div id="player-hands">
      <div class="hand active">
        <div class="cards">
          <div class="card"><span class="card-rank">A</span><span class="card-suit">♠</span></div>
          <div class="card red"><span class="card-rank">K</span><span class="card-suit">♥</span></div>
        </div>
        <div class="hand-value">BLACKJACK! <span class="bet-amount">$25</span></div>
      </div>
    </div>
  </div>
  <div id="controls">
    <div id="betting-controls">
      <div id="betting-hint" class="advantage-strong">
        <div class="hint-recommendation">
          <span class="hint-units">6 units — Strong advantage</span>
          <span class="hint-edge">Player edge: +1.5%</span>
        </div>
        <div class="hint-count">TC: <span>+4.1</span></div>
      </div>
      <input type="number" id="bet-amount" value="150">
      <button id="btn-bet">Place Bet (B)</button>
    </div>
  </div>
</div>
</div>
""",
    },
}

TEMPLATE = """<!-- @dsCard group="{group}" -->
<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{name}</title>
<style>
{css}
{overrides}
</style>
</head>
<body>
{body}
</body>
</html>
"""


OVERVIEW_HEADER = """
<div style="margin-bottom:34px">
  <div style="font-family:var(--font-display);font-size:34px;font-weight:700;letter-spacing:.12em;
              text-transform:uppercase;color:var(--ivory)">
    <span style="color:var(--gold)">♠</span> Blackjack Noir
    <span style="color:var(--card-red)">♦</span>
  </div>
  <div style="font-size:13px;color:var(--ivory-mute);max-width:60ch;margin-top:6px">
    Design system for the card-counting trainer — casino noir material world,
    gold on felt, serif display, monospace instruments. Generated from
    <code style="font-family:var(--font-mono)">frontend/css/</code> by
    <code style="font-family:var(--font-mono)">design-system/build.py</code>.
  </div>
</div>
"""


def build() -> list[str]:
    css = "\n".join((CSS_DIR / f).read_text() for f in CSS_FILES)
    DIST.mkdir(parents=True, exist_ok=True)
    written = []
    for filename, card in CARDS.items():
        html = TEMPLATE.format(
            group=card["group"],
            name=card["name"],
            css=css,
            overrides=PREVIEW_OVERRIDES,
            body=card["body"],
        )
        (DIST / filename).write_text(html)
        written.append(filename)

    # Single-page overview combining every card (for quick review/sharing)
    sections = []
    for filename, card in CARDS.items():
        sections.append(
            f'<section style="margin:0 0 44px">'
            f'<h2 style="font-family:var(--font-display);font-size:21px;font-weight:600;'
            f'letter-spacing:.14em;text-transform:uppercase;color:var(--gold-bright);'
            f'border-bottom:1px solid var(--panel-hairline);padding-bottom:8px;margin-bottom:18px">'
            f'{card["name"]} <span style="font-family:var(--font-body);font-size:11px;'
            f'color:var(--ivory-mute);letter-spacing:.18em">· {card["group"]}</span></h2>'
            f'{card["body"]}</section>'
        )
    overview = TEMPLATE.format(
        group="Overview",
        name="Blackjack Noir — Design System",
        css=css,
        overrides=PREVIEW_OVERRIDES,
        body=OVERVIEW_HEADER + "\n".join(sections),
    )
    (DIST / "overview.html").write_text(overview)
    written.append("overview.html")
    return written


if __name__ == "__main__":
    for name in build():
        print(f"built dist/{name}")
