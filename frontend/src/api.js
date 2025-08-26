const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:5000';

async function request(endpoint, options = {}) {
    const response = await fetch(`${API_URL}${endpoint}`, {
        ...options,
        headers: {
            'Content-Type': 'application/json',
            ...options.headers,
        },
    });

    if (!response.ok) {
        const error = new Error();
        error.status = response.status;
        const contentType = response.headers.get("content-type");
        if (contentType && contentType.indexOf("application/json") !== -1) {
            try {
                const errorData = await response.json();
                error.message = errorData.error || `HTTP error! status: ${response.status}`;
            } catch {
                error.message = `HTTP error! status: ${response.status}`;
            }
        } else {
            try {
                const errorText = await response.text();
                error.message = errorText || `HTTP error! status: ${response.status}`;
            } catch {
                error.message = `HTTP error! status: ${response.status}`;
            }
        }
        throw error;
    }

    const text = await response.text();
    try {
        // Handle empty response body
        if (text) {
            return JSON.parse(text);
        }
        return null;
    } catch {
        return text;
    }
}

export const createGame = () => request('/api/games/create', { method: 'POST' });

export const joinGame = (game_code, name) => {
    return request('/api/games/join', {
        method: 'POST',
        body: JSON.stringify({ game_code, name }),
    });
};

export const getGameState = (game_code) => request(`/api/games/${game_code}/state`);

export const submitStory = (game_code, player_id, story) => {
    return request(`/api/games/${game_code}/stories`, {
        method: 'POST',
        body: JSON.stringify({ player_id, story }),
    });
};

export const startGame = (game_code, controller_id) => {
    return request(`/api/games/${game_code}/start`, {
        method: 'POST',
        body: JSON.stringify({ controller_id }),
    });
};

export const advanceRound = (game_code, controller_id) => {
    return request(`/api/games/${game_code}/advance`, {
        method: 'POST',
        body: JSON.stringify({ controller_id }),
    });
};