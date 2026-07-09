/**
 * REST helpers with session identity
 */

export function getSessionId() {
    let id = localStorage.getItem('sessionId');
    if (!id) {
        id = 'sess_' + Math.random().toString(36).substring(2, 15);
        localStorage.setItem('sessionId', id);
    }
    return id;
}

function headers() {
    return {
        'Content-Type': 'application/json',
        'X-Session-ID': getSessionId(),
    };
}

export async function apiGet(path) {
    const response = await fetch(path, { headers: headers() });
    return response.json();
}

export async function apiPost(path, body = {}) {
    const response = await fetch(path, {
        method: 'POST',
        headers: headers(),
        body: JSON.stringify(body),
    });
    return response.json();
}

export async function apiDelete(path) {
    const response = await fetch(path, { method: 'DELETE', headers: headers() });
    return response.json();
}
