/**
 * Client-side basic strategy tables and index-play deviations.
 *
 * Temporary: used for in-play hints and the reference chart until decision
 * grading moves server-side (core/strategy is the source of truth there).
 * Tables assume 6-deck S17 DAS.
 */

// Keys: dealer upcard (2-11 where 11=A), Values: action
// (H=Hit, S=Stand, D=Double, P=Split, R=Surrender)
export const STRATEGY_TABLES = {
    // Hard totals: player total -> { dealer upcard -> action }
    hard: {
        5:  { 2:'H', 3:'H', 4:'H', 5:'H', 6:'H', 7:'H', 8:'H', 9:'H', 10:'H', 11:'H' },
        6:  { 2:'H', 3:'H', 4:'H', 5:'H', 6:'H', 7:'H', 8:'H', 9:'H', 10:'H', 11:'H' },
        7:  { 2:'H', 3:'H', 4:'H', 5:'H', 6:'H', 7:'H', 8:'H', 9:'H', 10:'H', 11:'H' },
        8:  { 2:'H', 3:'H', 4:'H', 5:'H', 6:'H', 7:'H', 8:'H', 9:'H', 10:'H', 11:'H' },
        9:  { 2:'H', 3:'D', 4:'D', 5:'D', 6:'D', 7:'H', 8:'H', 9:'H', 10:'H', 11:'H' },
        10: { 2:'D', 3:'D', 4:'D', 5:'D', 6:'D', 7:'D', 8:'D', 9:'D', 10:'H', 11:'H' },
        11: { 2:'D', 3:'D', 4:'D', 5:'D', 6:'D', 7:'D', 8:'D', 9:'D', 10:'D', 11:'D' },
        12: { 2:'H', 3:'H', 4:'S', 5:'S', 6:'S', 7:'H', 8:'H', 9:'H', 10:'H', 11:'H' },
        13: { 2:'S', 3:'S', 4:'S', 5:'S', 6:'S', 7:'H', 8:'H', 9:'H', 10:'H', 11:'H' },
        14: { 2:'S', 3:'S', 4:'S', 5:'S', 6:'S', 7:'H', 8:'H', 9:'H', 10:'H', 11:'H' },
        15: { 2:'S', 3:'S', 4:'S', 5:'S', 6:'S', 7:'H', 8:'H', 9:'H', 10:'R', 11:'R' },
        16: { 2:'S', 3:'S', 4:'S', 5:'S', 6:'S', 7:'H', 8:'H', 9:'R', 10:'R', 11:'R' },
        17: { 2:'S', 3:'S', 4:'S', 5:'S', 6:'S', 7:'S', 8:'S', 9:'S', 10:'S', 11:'S' },
        18: { 2:'S', 3:'S', 4:'S', 5:'S', 6:'S', 7:'S', 8:'S', 9:'S', 10:'S', 11:'S' },
        19: { 2:'S', 3:'S', 4:'S', 5:'S', 6:'S', 7:'S', 8:'S', 9:'S', 10:'S', 11:'S' },
        20: { 2:'S', 3:'S', 4:'S', 5:'S', 6:'S', 7:'S', 8:'S', 9:'S', 10:'S', 11:'S' },
        21: { 2:'S', 3:'S', 4:'S', 5:'S', 6:'S', 7:'S', 8:'S', 9:'S', 10:'S', 11:'S' }
    },
    // Soft totals: player total -> { dealer upcard -> action }
    soft: {
        13: { 2:'H', 3:'H', 4:'H', 5:'D', 6:'D', 7:'H', 8:'H', 9:'H', 10:'H', 11:'H' },
        14: { 2:'H', 3:'H', 4:'H', 5:'D', 6:'D', 7:'H', 8:'H', 9:'H', 10:'H', 11:'H' },
        15: { 2:'H', 3:'H', 4:'D', 5:'D', 6:'D', 7:'H', 8:'H', 9:'H', 10:'H', 11:'H' },
        16: { 2:'H', 3:'H', 4:'D', 5:'D', 6:'D', 7:'H', 8:'H', 9:'H', 10:'H', 11:'H' },
        17: { 2:'H', 3:'D', 4:'D', 5:'D', 6:'D', 7:'H', 8:'H', 9:'H', 10:'H', 11:'H' },
        18: { 2:'D', 3:'D', 4:'D', 5:'D', 6:'D', 7:'S', 8:'S', 9:'H', 10:'H', 11:'H' },
        19: { 2:'S', 3:'S', 4:'S', 5:'S', 6:'D', 7:'S', 8:'S', 9:'S', 10:'S', 11:'S' },
        20: { 2:'S', 3:'S', 4:'S', 5:'S', 6:'S', 7:'S', 8:'S', 9:'S', 10:'S', 11:'S' },
        21: { 2:'S', 3:'S', 4:'S', 5:'S', 6:'S', 7:'S', 8:'S', 9:'S', 10:'S', 11:'S' }
    },
    // Pairs: pair rank (2-11 where 11=A) -> { dealer upcard -> action }
    pairs: {
        2:  { 2:'P', 3:'P', 4:'P', 5:'P', 6:'P', 7:'P', 8:'H', 9:'H', 10:'H', 11:'H' },
        3:  { 2:'P', 3:'P', 4:'P', 5:'P', 6:'P', 7:'P', 8:'H', 9:'H', 10:'H', 11:'H' },
        4:  { 2:'H', 3:'H', 4:'H', 5:'P', 6:'P', 7:'H', 8:'H', 9:'H', 10:'H', 11:'H' },
        5:  { 2:'D', 3:'D', 4:'D', 5:'D', 6:'D', 7:'D', 8:'D', 9:'D', 10:'H', 11:'H' },
        6:  { 2:'P', 3:'P', 4:'P', 5:'P', 6:'P', 7:'H', 8:'H', 9:'H', 10:'H', 11:'H' },
        7:  { 2:'P', 3:'P', 4:'P', 5:'P', 6:'P', 7:'P', 8:'H', 9:'H', 10:'H', 11:'H' },
        8:  { 2:'P', 3:'P', 4:'P', 5:'P', 6:'P', 7:'P', 8:'P', 9:'P', 10:'P', 11:'P' },
        9:  { 2:'P', 3:'P', 4:'P', 5:'P', 6:'P', 7:'S', 8:'P', 9:'P', 10:'S', 11:'S' },
        10: { 2:'S', 3:'S', 4:'S', 5:'S', 6:'S', 7:'S', 8:'S', 9:'S', 10:'S', 11:'S' },
        11: { 2:'P', 3:'P', 4:'P', 5:'P', 6:'P', 7:'P', 8:'P', 9:'P', 10:'P', 11:'P' }
    }
};

// Illustrious 18 + Fab 4 deviations
// Format: { key: 'playerTotal-dealerUpcard-handType', threshold: TC, action, direction: 'gte'|'lte' }
export const DEVIATIONS = [
    // Illustrious 18
    { key: '16-10-hard', threshold: 0, action: 'S', direction: 'gte', description: 'Stand 16 vs 10 at TC 0+' },
    { key: '15-10-hard', threshold: 4, action: 'S', direction: 'gte', description: 'Stand 15 vs 10 at TC +4+' },
    { key: '10-10-hard', threshold: 4, action: 'D', direction: 'gte', description: 'Double 10 vs 10 at TC +4+' },
    { key: '10-11-hard', threshold: 4, action: 'D', direction: 'gte', description: 'Double 10 vs A at TC +4+' },
    { key: '12-3-hard', threshold: 2, action: 'S', direction: 'gte', description: 'Stand 12 vs 3 at TC +2+' },
    { key: '12-2-hard', threshold: 3, action: 'S', direction: 'gte', description: 'Stand 12 vs 2 at TC +3+' },
    { key: '12-4-hard', threshold: 0, action: 'H', direction: 'lte', description: 'Hit 12 vs 4 at TC 0 or less' },
    { key: '12-5-hard', threshold: -2, action: 'H', direction: 'lte', description: 'Hit 12 vs 5 at TC -2 or less' },
    { key: '12-6-hard', threshold: -1, action: 'H', direction: 'lte', description: 'Hit 12 vs 6 at TC -1 or less' },
    { key: '13-2-hard', threshold: -1, action: 'H', direction: 'lte', description: 'Hit 13 vs 2 at TC -1 or less' },
    { key: '13-3-hard', threshold: -2, action: 'H', direction: 'lte', description: 'Hit 13 vs 3 at TC -2 or less' },
    { key: '11-11-hard', threshold: 1, action: 'D', direction: 'gte', description: 'Double 11 vs A at TC +1+' },
    { key: '9-2-hard', threshold: 1, action: 'D', direction: 'gte', description: 'Double 9 vs 2 at TC +1+' },
    { key: '9-7-hard', threshold: 3, action: 'D', direction: 'gte', description: 'Double 9 vs 7 at TC +3+' },
    { key: '8-6-hard', threshold: 2, action: 'D', direction: 'gte', description: 'Double 8 vs 6 at TC +2+' },
    // Fab 4 Surrenders
    { key: '14-10-hard', threshold: 3, action: 'R', direction: 'gte', description: 'Surrender 14 vs 10 at TC +3+' },
    { key: '15-9-hard', threshold: 2, action: 'R', direction: 'gte', description: 'Surrender 15 vs 9 at TC +2+' },
    { key: '15-11-hard', threshold: 1, action: 'R', direction: 'gte', description: 'Surrender 15 vs A at TC +1+' },
    { key: '14-11-hard', threshold: 3, action: 'R', direction: 'gte', description: 'Surrender 14 vs A at TC +3+' }
];

export const ACTION_NAMES = { 'H': 'HIT', 'S': 'STAND', 'D': 'DOUBLE', 'P': 'SPLIT', 'R': 'SURRENDER' };

export function getActionClass(action) {
    const classes = {
        'H': 'action-hit',
        'S': 'action-stand',
        'D': 'action-double',
        'P': 'action-split',
        'R': 'action-surrender'
    };
    return classes[action] || 'action-hit';
}

export function checkDeviation(playerValue, dealerUpcard, isSoft, isPair, trueCount) {
    if (isPair) return null; // No pair deviations in I18/Fab4

    const handType = isSoft ? 'soft' : 'hard';
    const key = `${playerValue}-${dealerUpcard}-${handType}`;

    for (const dev of DEVIATIONS) {
        if (dev.key === key) {
            const shouldApply = dev.direction === 'gte'
                ? trueCount >= dev.threshold
                : trueCount <= dev.threshold;

            if (shouldApply) {
                return dev;
            }
        }
    }

    return null;
}

export function getBestPlay(handInfo, trueCount = 0) {
    const { playerValue, dealerUpcard, isPair, isSoft, pairRank } = handInfo;

    // Check for deviation first
    const deviation = checkDeviation(playerValue, dealerUpcard, isSoft, isPair, trueCount);
    if (deviation) {
        return {
            action: deviation.action,
            reason: deviation.description,
            isDeviation: true
        };
    }

    // Look up basic strategy
    let action;
    let handType;

    if (isPair) {
        action = STRATEGY_TABLES.pairs[pairRank]?.[dealerUpcard];
        handType = `Pair of ${pairRank === 11 ? 'Aces' : pairRank}s`;
    } else if (isSoft) {
        action = STRATEGY_TABLES.soft[playerValue]?.[dealerUpcard];
        handType = `Soft ${playerValue}`;
    } else {
        action = STRATEGY_TABLES.hard[playerValue]?.[dealerUpcard];
        handType = `Hard ${playerValue}`;
    }

    if (!action) {
        action = playerValue >= 17 ? 'S' : 'H';
    }

    return {
        action: action,
        reason: `${ACTION_NAMES[action]} - ${handType}`,
        isDeviation: false
    };
}

export function getBettingHint(trueCount) {
    // Each TC point ~ 0.5% edge change; house edge at TC 0 ~ -0.5%
    const baseEdge = -0.5;
    const edgePerTC = 0.5;
    const playerEdge = baseEdge + (trueCount * edgePerTC);

    let units, level, message;

    if (trueCount < 1) {
        units = 1;
        level = 'negative';
        message = '1 unit - House edge';
    } else if (trueCount < 2) {
        units = 1;
        level = 'breakeven';
        message = '1 unit - Breakeven zone';
    } else if (trueCount < 3) {
        units = 2;
        level = 'positive';
        message = '2 units - Player advantage';
    } else if (trueCount < 4) {
        units = 4;
        level = 'positive';
        message = '4 units - Player advantage';
    } else if (trueCount < 5) {
        units = 6;
        level = 'strong';
        message = '6 units - Strong advantage';
    } else {
        units = Math.min(12, Math.floor(trueCount * 1.5));
        level = 'strong';
        message = `${units} units - Strong advantage`;
    }

    return {
        units: units,
        level: level,
        message: message,
        edge: playerEdge,
        trueCount: trueCount
    };
}
