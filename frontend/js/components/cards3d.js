/**
 * Keyed-DOM card rendering for the table with 3D flips and deal-in motion.
 *
 * Unlike the string-based renderCard (still used by drills), this component
 * keeps stable DOM nodes per card position, so:
 *  - new cards animate in from the shoe exactly once,
 *  - the dealer's hole card flips over in place on reveal,
 *  - hover tilt and win glow attach to persistent elements.
 */

import { formatRank, getSuitSymbol } from './cards.js';
import { reducedMotion } from '../juice/loop.js';

const RED_SUITS = new Set(['♥', '♦']);

function isHidden(card) {
    return card.hidden || card.rank === '?';
}

function cardSignature(card) {
    return isHidden(card) ? '??' : `${card.rank}${card.suit}`;
}

function buildCardEl() {
    const el = document.createElement('div');
    el.className = 'card card3';
    el.innerHTML = `
        <div class="card-inner">
            <div class="card-face card-front">
                <span class="card-rank"></span>
                <span class="card-suit"></span>
            </div>
            <div class="card-face card-back"><span>♠</span></div>
        </div>`;
    return el;
}

function setFace(el, card) {
    el.dataset.sig = cardSignature(card);
    if (isHidden(card)) {
        el.classList.add('is-down');
        return;
    }
    const suit = getSuitSymbol(card.suit);
    el.querySelector('.card-rank').textContent = formatRank(card.rank);
    el.querySelector('.card-suit').textContent = suit;
    el.classList.toggle('red', RED_SUITS.has(suit));
    el.classList.remove('is-down');
}

/** Animate a newly-inserted card from the shoe anchor to its slot. */
function dealIn(el) {
    if (reducedMotion.matches) return;
    const anchor = document.getElementById('shoe-anchor');
    if (!anchor) {
        el.classList.add('deal-fallback');
        return;
    }
    const from = anchor.getBoundingClientRect();
    const to = el.getBoundingClientRect();
    const dx = from.left + from.width / 2 - (to.left + to.width / 2);
    const dy = from.top + from.height / 2 - (to.top + to.height / 2);

    el.style.transition = 'none';
    el.style.transform = `translate(${dx}px, ${dy}px) rotate(7deg) scale(0.86)`;
    el.style.opacity = '0.85';
    void el.offsetWidth;
    el.style.transition = 'transform 340ms var(--ease-back), opacity 200ms linear';
    el.style.transform = '';
    el.style.opacity = '';
    el.addEventListener('transitionend', () => {
        el.style.transition = '';
    }, { once: true });
}

/** Reconcile one .cards container against a list of card dicts. */
function syncCards(container, cards, keyPrefix) {
    const existing = new Map();
    for (const el of container.querySelectorAll(':scope > .card3')) {
        existing.set(el.dataset.key, el);
    }

    cards.forEach((card, i) => {
        const key = `${keyPrefix}:${i}`;
        let el = existing.get(key);
        existing.delete(key);

        if (!el) {
            el = buildCardEl();
            el.dataset.key = key;
            setFace(el, card);
            container.appendChild(el);
            dealIn(el);
            return;
        }

        const sig = cardSignature(card);
        if (el.dataset.sig !== sig) {
            if (el.dataset.sig === '??' && !isHidden(card)) {
                // Hole card reveal: set the front, then flip in place
                setFace(el, card);
            } else {
                // Card identity changed (e.g. split rearrangement)
                setFace(el, card);
            }
        }
    });

    // Remove leftovers (new round / split rearrangement)
    for (const el of existing.values()) {
        el.remove();
    }
}

function handStatus(hand) {
    if (hand.is_blackjack) return 'BLACKJACK!';
    if (hand.is_busted) return 'BUST';
    return (hand.is_soft ? 'Soft ' : '') + hand.value;
}

/**
 * Reconcile the dealer area and all player hands from a state snapshot.
 */
export function syncTable(state) {
    const dealerContainer = document.getElementById('dealer-cards');
    if (dealerContainer) {
        syncCards(dealerContainer, state.dealer_hand?.cards ?? [], 'd');
    }

    const handsContainer = document.getElementById('player-hands');
    if (!handsContainer) return;

    const hands = (state.player_hands && state.player_hands.length > 0)
        ? state.player_hands
        : [{ cards: [], value: '', is_soft: false }];

    // Ensure the right number of .hand wrappers
    let handEls = [...handsContainer.querySelectorAll(':scope > .hand')];
    while (handEls.length < hands.length) {
        const el = document.createElement('div');
        el.className = 'hand';
        el.id = `hand-${handEls.length}`;
        el.innerHTML = '<div class="cards"></div><div class="hand-value"></div>';
        handsContainer.appendChild(el);
        handEls.push(el);
    }
    while (handEls.length > hands.length) {
        handEls.pop().remove();
    }

    hands.forEach((hand, i) => {
        const handEl = handEls[i];
        const isActive = i === state.current_hand_index && state.state === 'PLAYER_TURN';
        handEl.classList.toggle('active', isActive);
        handEl.classList.toggle('busted', !!hand.is_busted);
        handEl.classList.toggle('blackjack', !!hand.is_blackjack);

        syncCards(handEl.querySelector('.cards'), hand.cards ?? [], `p${i}`);

        const valueEl = handEl.querySelector('.hand-value');
        if (!hand.cards || hand.cards.length === 0) {
            valueEl.textContent = '';
        } else {
            valueEl.innerHTML = '';
            valueEl.append(handStatus(hand));
            if (hand.bet) {
                const bet = document.createElement('span');
                bet.className = 'bet-amount';
                bet.textContent = `$${hand.bet}`;
                valueEl.append(' ', bet);
            }
        }
    });
}

/** Balatro-style hover tilt on player cards (delegated, motion-safe). */
export function initCardTilt() {
    const container = document.getElementById('player-hands');
    if (!container) return;

    container.addEventListener('pointermove', (e) => {
        if (reducedMotion.matches) return;
        const card = e.target.closest('.card3');
        if (!card || !container.contains(card)) return;
        const rect = card.getBoundingClientRect();
        const px = (e.clientX - rect.left) / rect.width - 0.5;
        const py = (e.clientY - rect.top) / rect.height - 0.5;
        card.style.setProperty('--tilt-x', `${(-py * 14).toFixed(2)}deg`);
        card.style.setProperty('--tilt-y', `${(px * 16).toFixed(2)}deg`);
        card.classList.add('tilting');
    });

    container.addEventListener('pointerout', (e) => {
        const card = e.target.closest('.card3');
        if (!card) return;
        card.style.setProperty('--tilt-x', '0deg');
        card.style.setProperty('--tilt-y', '0deg');
        card.classList.remove('tilting');
    });
}
