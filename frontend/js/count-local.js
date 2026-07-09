/**
 * Client-side count tracking.
 *
 * Temporary: replaced by server-authoritative counts once the WebSocket
 * session computes them (the server also counts the dealer hole card at
 * reveal time, which this tracker never sees).
 */

export class CountTracker {
    constructor(system = 'hilo') {
        this.system = system;
        this.runningCount = 0;
        this.cardsSeen = 0;
        this.decksRemaining = 6;
        this.totalDecks = 6;

        this.tagValues = this.getTagValues(system);
    }

    /**
     * Normalize rank to a standard format for counting
     */
    normalizeRank(rank) {
        const rankMap = {
            // Full names
            'ACE': 'A', 'KING': 'K', 'QUEEN': 'Q', 'JACK': 'J',
            'TEN': '10', 'NINE': '9', 'EIGHT': '8', 'SEVEN': '7',
            'SIX': '6', 'FIVE': '5', 'FOUR': '4', 'THREE': '3', 'TWO': '2',
            // Already abbreviated
            'A': 'A', 'K': 'K', 'Q': 'Q', 'J': 'J',
            '10': '10', '9': '9', '8': '8', '7': '7',
            '6': '6', '5': '5', '4': '4', '3': '3', '2': '2'
        };
        return rankMap[rank.toUpperCase()] || rank;
    }

    /**
     * Get tag values for a counting system
     */
    getTagValues(system) {
        const systems = {
            hilo: {
                '2': 1, '3': 1, '4': 1, '5': 1, '6': 1,
                '7': 0, '8': 0, '9': 0,
                '10': -1, 'J': -1, 'Q': -1, 'K': -1, 'A': -1
            },
            ko: {
                '2': 1, '3': 1, '4': 1, '5': 1, '6': 1, '7': 1,
                '8': 0, '9': 0,
                '10': -1, 'J': -1, 'Q': -1, 'K': -1, 'A': -1
            },
            omega2: {
                '2': 1, '3': 1, '4': 2, '5': 2, '6': 2, '7': 1,
                '8': 0, '9': -1,
                '10': -2, 'J': -2, 'Q': -2, 'K': -2, 'A': 0
            },
            wong_halves: {
                '2': 0.5, '3': 1, '4': 1, '5': 1.5, '6': 1, '7': 0.5,
                '8': 0, '9': -0.5,
                '10': -1, 'J': -1, 'Q': -1, 'K': -1, 'A': -1
            }
        };
        return systems[system] || systems.hilo;
    }

    /**
     * Count a card
     */
    countCard(rank) {
        const normalizedRank = this.normalizeRank(rank);
        const tag = this.tagValues[normalizedRank] || 0;
        this.runningCount += tag;
        this.cardsSeen++;
        this.decksRemaining = Math.max(1, (this.totalDecks * 52 - this.cardsSeen) / 52);
        this.updateDisplay();
        return tag;
    }

    /**
     * Calculate true count
     */
    get trueCount() {
        return this.runningCount / this.decksRemaining;
    }

    /**
     * Update the count display
     */
    updateDisplay() {
        const rcEl = document.querySelector('#running-count span');
        const tcEl = document.querySelector('#true-count span');
        const cardsEl = document.querySelector('#cards-remaining span');

        if (rcEl) {
            // Show integer for whole numbers, 1 decimal for half counts
            if (Number.isInteger(this.runningCount)) {
                rcEl.textContent = this.runningCount;
            } else {
                rcEl.textContent = this.runningCount.toFixed(1);
            }
        }
        if (tcEl) {
            const tc = this.trueCount;
            tcEl.textContent = Number.isInteger(tc) ? tc : tc.toFixed(1);
        }
        if (cardsEl) cardsEl.textContent = Math.round(this.decksRemaining * 52);
    }

    /**
     * Reset count for new shoe
     */
    reset(numDecks = 6) {
        this.runningCount = 0;
        this.cardsSeen = 0;
        this.totalDecks = numDecks;
        this.decksRemaining = numDecks;
        this.updateDisplay();
    }

    /**
     * Switch counting system
     */
    setSystem(system) {
        this.system = system;
        this.tagValues = this.getTagValues(system);
        this.reset(this.totalDecks);
    }
}
