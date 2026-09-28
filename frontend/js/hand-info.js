/**
 * Extract strategy-relevant hand facts from a game state
 */

import { getCardNumericRank } from './components/cards.js';

export function getDealerUpcard(state) {
    if (!state?.dealer_hand?.cards) return null;
    const visibleCard = state.dealer_hand.cards.find(c => !c.hidden && c.rank !== '?');
    if (!visibleCard) return null;
    return getCardNumericRank(visibleCard);
}

export function getHandInfo(state) {
    if (!state?.player_hands || state.player_hands.length === 0) return null;

    const handIndex = state.current_hand_index || 0;
    const hand = state.player_hands[handIndex];
    if (!hand || !hand.cards || hand.cards.length < 2) return null;

    const dealerShowing = state.dealer_showing || getDealerUpcard(state);
    if (!dealerShowing) return null;

    // Convert dealer showing to numeric value
    let dealerUpcard = dealerShowing;
    if (typeof dealerUpcard === 'string') {
        const rankMap = { 'A': 11, 'K': 10, 'Q': 10, 'J': 10, 'T': 10 };
        dealerUpcard = rankMap[dealerUpcard] || parseInt(dealerUpcard, 10);
    }

    // Check if pair
    let isPair = false;
    let pairRank = null;
    if (hand.cards.length === 2) {
        const rank1 = getCardNumericRank(hand.cards[0]);
        const rank2 = getCardNumericRank(hand.cards[1]);
        if (rank1 === rank2) {
            isPair = true;
            pairRank = rank1;
        }
    }

    return {
        playerValue: hand.value,
        dealerUpcard: dealerUpcard,
        isPair: isPair,
        isSoft: hand.is_soft,
        pairRank: pairRank
    };
}
