/**
 * Charts and statistics visualization
 */

class StatsTracker {
    constructor() {
        this.handsPlayed = 0;
        this.wins = 0;
        this.losses = 0;
        this.pushes = 0;
        this.blackjacks = 0;
        this.totalWagered = 0;
        this.netResult = 0;
        this.history = [];
    }

    /**
     * Record a hand result
     */
    recordHand(result) {
        this.handsPlayed++;
        this.totalWagered += result.wager || 0;

        switch (result.outcome) {
            case 'win':
                this.wins++;
                this.netResult += result.amount;
                break;
            case 'blackjack':
                this.wins++;
                this.blackjacks++;
                this.netResult += result.amount;
                break;
            case 'lose':
                this.losses++;
                this.netResult -= result.amount;
                break;
            case 'push':
                this.pushes++;
                break;
            case 'surrender':
                this.losses++;
                this.netResult -= result.amount / 2;
                break;
        }

        this.history.push({
            timestamp: Date.now(),
            ...result,
            runningTotal: this.netResult
        });

        this.updateDisplay();
    }

    /**
     * Calculate win rate
     */
    get winRate() {
        if (this.handsPlayed === 0) return 0;
        return (this.wins / this.handsPlayed) * 100;
    }

    /**
     * Update the stats display
     */
    updateDisplay() {
        const handsEl = document.querySelector('#hands-played span');
        const winRateEl = document.querySelector('#win-rate span');
        const netResultEl = document.querySelector('#net-result span');

        if (handsEl) handsEl.textContent = this.handsPlayed;
        if (winRateEl) winRateEl.textContent = this.winRate.toFixed(1) + '%';
        if (netResultEl) {
            netResultEl.textContent = (this.netResult >= 0 ? '+' : '') + '$' + this.netResult.toFixed(0);
            netResultEl.style.color = this.netResult >= 0 ? '#28a745' : '#dc3545';
        }
    }

    /**
     * Reset all stats
     */
    reset() {
        this.handsPlayed = 0;
        this.wins = 0;
        this.losses = 0;
        this.pushes = 0;
        this.blackjacks = 0;
        this.totalWagered = 0;
        this.netResult = 0;
        this.history = [];
        this.updateDisplay();
    }

    /**
     * Export stats as JSON
     */
    toJSON() {
        return {
            handsPlayed: this.handsPlayed,
            wins: this.wins,
            losses: this.losses,
            pushes: this.pushes,
            blackjacks: this.blackjacks,
            winRate: this.winRate,
            totalWagered: this.totalWagered,
            netResult: this.netResult,
            history: this.history
        };
    }
}


class CountTracker {
    constructor(system = 'hilo') {
        this.system = system;
        this.runningCount = 0;
        this.cardsSeen = 0;
        this.decksRemaining = 6;
        this.totalDecks = 6;

        // Tag values for different systems
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
        if (tcEl) tcEl.textContent = this.trueCount.toFixed(1);
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

// Export for use in other scripts
window.StatsTracker = StatsTracker;
window.CountTracker = CountTracker;
