# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

A professional blackjack card counting trainer: **statistical engine first, game second**. The application is an advanced blackjack calculator with a playable interface layered on top, designed for progressive skill development.

## Technology Stack

- Python 3.11+
- FastAPI with WebSocket support
- Frontend: Vanilla JS + htmx
- Session Storage: Redis (with in-memory fallback for local dev)
- Testing: pytest with hypothesis for property-based testing
- Pydantic for all data models
- `transitions` library for game state machine

## Architecture

The core engine (`core/`) must be **100% UI-agnostic** with zero presentation layer dependencies. Communication happens through return values and event subscriptions—no print statements or direct input.

```
core/           # Pure Python, no UI dependencies
├── cards.py    # Card, Deck, Shoe classes
├── hand.py     # Hand evaluation
├── counting/   # Hi-Lo, KO, Omega II, Wong Halves systems
├── strategy/   # Basic strategy matrices, Illustrious 18 deviations
├── statistics/ # Probability engine, house edge, Kelly criterion
└── game/       # State machine, event system
api/            # FastAPI layer
frontend/       # Static files (HTML/CSS/JS)
tests/          # pytest tests mirroring core/ and api/ structure
```

## Development Commands

```bash
# Setup
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Run API server
uvicorn api.main:app --reload

# Run tests
pytest
pytest tests/core/test_counting.py -v    # Single test file
pytest -k "test_hilo"                     # Run tests matching pattern

# Type checking (if mypy is used)
mypy core/
```

## Key Implementation Notes

1. **Counting systems** sum correctly for a full deck: Hi-Lo = 0, KO = +4
2. **Strategy tables** are pre-computed dictionaries for O(1) lookup, not runtime calculation
3. **Use Decimal** for money calculations; floats are acceptable for count values
4. **Cards are immutable** (frozen dataclasses)
5. **State machine** governs game flow: WAITING_FOR_BET → DEALING → PLAYER_TURN → DEALER_TURN → RESOLVING → ROUND_COMPLETE
6. **Illustrious 18** index plays and **Fab 4** surrender indices are the core deviations to implement

## Testing Requirements

- Counting systems: verify full deck sums to expected value
- Strategy matrices: validate against published basic strategy charts
- Probability calculations: ensure distributions sum to 1.0
- Game state: only valid transitions are permitted
