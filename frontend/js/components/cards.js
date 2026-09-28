/**
 * Card rendering
 */

export function formatRank(rank) {
    const rankMap = {
        'ACE': 'A', 'KING': 'K', 'QUEEN': 'Q', 'JACK': 'J',
        'TEN': '10', 'NINE': '9', 'EIGHT': '8', 'SEVEN': '7',
        'SIX': '6', 'FIVE': '5', 'FOUR': '4', 'THREE': '3', 'TWO': '2'
    };
    return rankMap[rank] || rank;
}

export function getSuitSymbol(suit) {
    const symbols = {
        'CLUBS': '♣', 'DIAMONDS': '♦', 'HEARTS': '♥', 'SPADES': '♠',
        '♣': '♣', '♦': '♦', '♥': '♥', '♠': '♠'
    };
    return symbols[suit] || suit;
}

export function getCardNumericRank(card) {
    if (!card || !card.rank) return null;
    const rankMap = {
        'ACE': 11, 'KING': 10, 'QUEEN': 10, 'JACK': 10, 'TEN': 10,
        'NINE': 9, 'EIGHT': 8, 'SEVEN': 7, 'SIX': 6, 'FIVE': 5,
        'FOUR': 4, 'THREE': 3, 'TWO': 2,
        'A': 11, 'K': 10, 'Q': 10, 'J': 10, 'T': 10,
        '10': 10, '9': 9, '8': 8, '7': 7, '6': 6, '5': 5, '4': 4, '3': 3, '2': 2
    };
    return rankMap[card.rank] || parseInt(card.rank, 10) || null;
}

export function renderCard(card) {
    if (card.hidden || card.rank === '?') {
        return '<div class="card face-down"><span>?</span></div>';
    }

    const suit = getSuitSymbol(card.suit);
    const isRed = suit === '♥' || suit === '♦';
    const displayRank = formatRank(card.rank);

    return `<div class="card ${isRed ? 'red' : ''}">
        <span class="card-rank">${displayRank}</span>
        <span class="card-suit">${suit}</span>
    </div>`;
}

export function renderHand(hand, index, isActive) {
    const activeClass = isActive ? 'active' : '';
    let statusText = '';

    if (hand.is_blackjack) {
        statusText = 'BLACKJACK!';
    } else if (hand.is_busted) {
        statusText = 'BUST';
    } else {
        statusText = (hand.is_soft ? 'Soft ' : '') + hand.value;
    }

    return `
        <div class="hand ${activeClass}" id="hand-${index}">
            <div class="cards">
                ${hand.cards.map(card => renderCard(card)).join('')}
            </div>
            <div class="hand-value">
                ${statusText}
                ${hand.bet ? ` <span class="bet-amount">$${hand.bet}</span>` : ''}
            </div>
        </div>
    `;
}
