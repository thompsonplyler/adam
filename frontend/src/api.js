const API_URL = 'http://localhost:5000';

async function request(endpoint, options = {}) {
    const response = await fetch(`${API_URL}${endpoint}`, {
        credentials: 'include',
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

export const login = (username, password) => {
    return request('/login', {
        method: 'POST',
        body: JSON.stringify({ username, password }),
    });
};

export const register = (username, password) => {
    return request('/users/add', {
        method: 'POST',
        body: JSON.stringify({ username, password }),
    });
};

export const createGame = () => request('/games/create', { method: 'POST' });

export const joinGame = (game_code) => {
    return request('/games/join', {
        method: 'POST',
        body: JSON.stringify({ game_code }),
    });
};

export const submitStory = (game_id, content) => {
    return request('/games/stories/submit', {
        method: 'POST',
        body: JSON.stringify({ game_id, content }),
    });
};

export const getGameState = (game_code) => request(`/games/${game_code}/state`);

export const startGame = (game_code) => request(`/games/${game_code}/start`, { method: 'POST' });

export const getNextStory = (game_code) => request(`/games/${game_code}/story`, { method: 'GET' });

export const submitGuess = (game_code, guessed_user_id) => {
    return request(`/games/${game_code}/guess`, {
        method: 'POST',
        body: JSON.stringify({ guessed_user_id }),
    });
};

export const getResults = (game_code) => request(`/games/${game_code}/results`, { method: 'GET' });

export const revealResults = (game_code) => request(`/games/${game_code}/reveal`, { method: 'POST' });

export const leaveGame = (game_code) => request(`/games/${game_code}/leave`, { method: 'POST' });

export const getActiveGames = () => request('/games/active', { method: 'GET' });

export const logout = () => request('/logout', { method: 'POST' });

export const checkLogin = () => request('/check_login'); 