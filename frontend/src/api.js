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
        const errorData = await response.json();
        throw new Error(errorData.error || `HTTP error! status: ${response.status}`);
    }
    return response.json();
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

export const createGame = async () => {
    const response = await fetch(`${API_URL}/games/create`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        credentials: 'include',
    });

    const responseBody = await response.text();

    if (!response.ok) {
        throw new Error(`Failed to create game: ${responseBody}`);
    }

    try {
        return JSON.parse(responseBody);
    } catch (e) {
        throw new Error(`Failed to parse server response: ${e.message}`);
    }
};

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

export const getNextStory = (game_code) => request(`/games/${game_code}/story`);

export const submitGuess = (game_code, guessed_user_id) => {
    return request(`/games/${game_code}/guess`, {
        method: 'POST',
        body: JSON.stringify({ guessed_user_id }),
    });
};

export const getResults = (game_code) => request(`/games/${game_code}/results`);

export const leaveGame = (game_code) => request(`/games/${game_code}/leave`, { method: 'POST' });

export const getActiveGames = () => request('/games/active');

export const logout = async () => {
    const response = await fetch(`${API_URL}/users/logout`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        credentials: 'include',
    });
    if (!response.ok) {
        throw new Error('Logout failed');
    }
    return await response.json();
}

export const checkLogin = async () => {
    const response = await fetch(`${API_URL}/users/check_login`, {
        method: 'GET',
        headers: {
            'Content-Type': 'application/json',
        },
        credentials: 'include',
    });
    if (!response.ok) {
        throw new Error('Not logged in');
    }
    return await response.json();
}; 