/**
 * In-session stats tally shown in the side panel
 */

export class StatsTracker {
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
