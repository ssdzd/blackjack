/**
 * WebSocket client for real-time game updates
 */

export class GameWebSocket {
    constructor() {
        this.ws = null;
        this.sessionId = null;
        this.reconnectAttempts = 0;
        this.maxReconnectAttempts = 5;
        this.reconnectDelay = 1000;
        this.handlers = new Map();
        this.pendingMessages = [];
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
            // Flush anything sent while the socket was still connecting
            const pending = this.pendingMessages.splice(0);
            pending.forEach(msg => this.ws.send(msg));
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
        const payload = JSON.stringify({ type, ...data });
        if (this.ws && this.ws.readyState === WebSocket.OPEN) {
            this.ws.send(payload);
        } else if (this.pendingMessages.length < 20) {
            // Queue until the socket opens (e.g. user acts during connect)
            this.pendingMessages.push(payload);
        } else {
            console.warn('WebSocket not connected; message dropped');
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
export class BlackjackClient extends GameWebSocket {
    placeBet(amount) {
        this.send('bet', { amount });
    }

    action(action) {
        this.send('action', { action });
    }

    hit() {
        this.action('hit');
    }

    stand() {
        this.action('stand');
    }

    double() {
        this.action('double');
    }

    split() {
        this.action('split');
    }

    surrender() {
        this.action('surrender');
    }

    insurance(take) {
        this.send('insurance', { take });
    }

    newRound() {
        this.send('new_round');
    }
}
