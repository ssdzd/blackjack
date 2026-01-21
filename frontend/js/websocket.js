/**
 * WebSocket client for real-time game updates
 */

class GameWebSocket {
    constructor() {
        this.ws = null;
        this.sessionId = null;
        this.reconnectAttempts = 0;
        this.maxReconnectAttempts = 5;
        this.reconnectDelay = 1000;
        this.handlers = new Map();
    }

    /**
     * Connect to the game WebSocket
     */
    connect(sessionId) {
        this.sessionId = sessionId;
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const wsUrl = `${protocol}//${window.location.host}/ws/game/${sessionId}`;

        this.ws = new WebSocket(wsUrl);

        this.ws.onopen = () => {
            console.log('WebSocket connected');
            this.reconnectAttempts = 0;
            this.emit('connected');
        };

        this.ws.onmessage = (event) => {
            const message = JSON.parse(event.data);
            this.handleMessage(message);
        };

        this.ws.onclose = () => {
            console.log('WebSocket disconnected');
            this.emit('disconnected');
            this.attemptReconnect();
        };

        this.ws.onerror = (error) => {
            console.error('WebSocket error:', error);
            this.emit('error', error);
        };
    }

    /**
     * Attempt to reconnect after disconnection
     */
    attemptReconnect() {
        if (this.reconnectAttempts >= this.maxReconnectAttempts) {
            console.log('Max reconnect attempts reached');
            this.emit('reconnect_failed');
            return;
        }

        this.reconnectAttempts++;
        const delay = this.reconnectDelay * Math.pow(2, this.reconnectAttempts - 1);

        console.log(`Attempting reconnect in ${delay}ms...`);
        setTimeout(() => {
            if (this.sessionId) {
                this.connect(this.sessionId);
            }
        }, delay);
    }

    /**
     * Handle incoming WebSocket message
     */
    handleMessage(message) {
        const { type, ...data } = message;
        this.emit(type, data);
        this.emit('message', message);
    }

    /**
     * Send a message to the server
     */
    send(type, data = {}) {
        if (this.ws && this.ws.readyState === WebSocket.OPEN) {
            this.ws.send(JSON.stringify({ type, ...data }));
        } else {
            console.warn('WebSocket not connected');
        }
    }

    /**
     * Register an event handler
     */
    on(event, handler) {
        if (!this.handlers.has(event)) {
            this.handlers.set(event, []);
        }
        this.handlers.get(event).push(handler);
    }

    /**
     * Remove an event handler
     */
    off(event, handler) {
        if (this.handlers.has(event)) {
            const handlers = this.handlers.get(event);
            const index = handlers.indexOf(handler);
            if (index !== -1) {
                handlers.splice(index, 1);
            }
        }
    }

    /**
     * Emit an event to all handlers
     */
    emit(event, data = {}) {
        if (this.handlers.has(event)) {
            this.handlers.get(event).forEach(handler => handler(data));
        }
    }

    /**
     * Disconnect the WebSocket
     */
    disconnect() {
        if (this.ws) {
            this.ws.close();
            this.ws = null;
        }
    }

    /**
     * Check if connected
     */
    get isConnected() {
        return this.ws && this.ws.readyState === WebSocket.OPEN;
    }
}

// Game-specific WebSocket commands
class BlackjackClient extends GameWebSocket {
    /**
     * Place a bet
     */
    placeBet(amount) {
        this.send('bet', { amount });
    }

    /**
     * Execute a player action
     */
    action(action) {
        this.send('action', { action });
    }

    /**
     * Hit
     */
    hit() {
        this.action('hit');
    }

    /**
     * Stand
     */
    stand() {
        this.action('stand');
    }

    /**
     * Double down
     */
    double() {
        this.action('double');
    }

    /**
     * Split
     */
    split() {
        this.action('split');
    }

    /**
     * Surrender
     */
    surrender() {
        this.action('surrender');
    }

    /**
     * Request new round
     */
    newRound() {
        this.send('new_round');
    }
}

// Export for use in other scripts
window.BlackjackClient = BlackjackClient;
