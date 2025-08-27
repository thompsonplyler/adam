const API_URL = (import.meta as any).env?.VITE_API_URL || (globalThis as any).process?.env?.API_URL || 'http://localhost:5000';

async function request<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
    const res = await fetch(`${API_URL}${endpoint}`, {
        ...options,
        headers: {
            'Content-Type': 'application/json',
            ...(options.headers || {}),
        },
    });
    if (!res.ok) {
        let message = `HTTP ${res.status}`;
        try {
            const data = await res.json();
            message = (data as any)?.error || message;
        } catch { }
        throw new Error(message);
    }
    const text = await res.text();
    return text ? (JSON.parse(text) as T) : (null as unknown as T);
}

export type Player = { id: number; name: string; has_submitted_story: boolean };
export type GameState = {
    id: number;
    game_code: string;
    status: 'lobby' | 'in_progress' | 'finished';
    stage?: 'round_intro' | 'guessing' | 'scoreboard' | 'finished';
    players: Player[];
    current_round?: number | null;
    total_rounds?: number | null;
    play_order?: number[] | null;
    current_story?: { id: number; content: string; author_id: number } | null;
    current_story_guess_count?: number;
    durations?: { round_intro?: number; guessing?: number; scoreboard?: number };
    stage_deadline?: number; // unix timestamp seconds
    round_history?: Array<{
        round: number;
        story_id: number;
        author_id: number;
        guesses: { guesser_id: number; guessed_player_id: number }[];
        correct_guessers: number[];
        author_points_awarded: number;
    }>;
};

export async function createGame(opts?: { game_mode?: string; stories_per_player?: number }): Promise<{ game_code: string }> {
    return request('/api/games/create', { method: 'POST', body: JSON.stringify(opts || {}) });
}

export async function getGameState(gameCode: string): Promise<GameState> {
    return request(`/api/games/${gameCode}/state`);
}


