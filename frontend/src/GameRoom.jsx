import { useState, useEffect, useRef } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { Button, Container, Title, Text, TextInput, Paper, SimpleGrid, Loader, Group, Stack, Textarea } from '@mantine/core';
import * as api from './api';
import { io } from 'socket.io-client';

function JoinGameForm({ onJoin, loading }) {
    const [playerName, setPlayerName] = useState('');

    const handleSubmit = (e) => {
        e.preventDefault();
        if (playerName.trim()) {
            onJoin(playerName.trim());
        }
    };

    return (
        <Paper withBorder shadow="md" p="lg" mt="lg">
            <Title order={3}>Join Game</Title>
            <form onSubmit={handleSubmit}>
                <Stack>
                    <TextInput
                        placeholder="Your Name"
                        label="Enter your name to join"
                        required
                        value={playerName}
                        onChange={(e) => setPlayerName(e.currentTarget.value)}
                    />
                    <Button type="submit" loading={loading}>
                        Join
                    </Button>
                </Stack>
            </form>
        </Paper>
    );
}


function PlayerLobby({ player, onStorySubmit, loading }) {
    const [story, setStory] = useState('');

    const handleSubmit = (e) => {
        e.preventDefault();
        if (story.trim()) {
            onStorySubmit(story.trim());
        }
    };

    return (
        <Paper withBorder shadow="md" p="lg" mt="lg">
            <Title order={3}>Welcome, {player.name}!</Title>
            <Text c="dimmed">The game will begin once everyone has submitted a story.</Text>

            <form onSubmit={handleSubmit}>
                <Stack mt="md">
                    <Textarea
                        placeholder="Once, I convinced everyone that..."
                        label="Your secret story"
                        required
                        autosize
                        minRows={4}
                        value={story}
                        onChange={(e) => setStory(e.currentTarget.value)}
                        disabled={player.has_submitted_story}
                    />
                    <Button
                        type="submit"
                        loading={loading}
                        disabled={player.has_submitted_story}
                    >
                        {player.has_submitted_story ? "Waiting for others..." : "Submit & Ready Up"}
                    </Button>
                </Stack>
            </form>
        </Paper>
    );
}


export function GameRoom() {
    const { gameCode } = useParams();
    const navigate = useNavigate();
    const [game, setGame] = useState(null);
    const [error, setError] = useState('');
    const [loading, setLoading] = useState(false);
    const socketRef = useRef(null);

    // Attempt to get player ID from session storage
    const [playerId, setPlayerId] = useState(() => sessionStorage.getItem(`player_id_${gameCode}`));

    useEffect(() => {
        const fetchGameState = async () => {
            try {
                const gameState = await api.getGameState(gameCode);
                setGame(gameState);
                setError('');
            } catch (err) {
                console.error("Failed to fetch game state:", err);
                setError(`Game not found or an error occurred. Code: ${gameCode}`);
                if (err.status === 404) {
                    navigate('/'); // Redirect to home if game not found
                }
            }
        };

        fetchGameState(); // Initial fetch
        const intervalId = setInterval(fetchGameState, 3000); // Poll every 3 seconds (kept as fallback)

        // Setup Socket.IO connection
        const baseUrl = import.meta.env.VITE_API_URL || 'http://localhost:5000';
        const socket = io(baseUrl + '/ws');
        socketRef.current = socket;
        socket.on('connect', () => {
            socket.emit('join_game', { game_code: gameCode });
        });
        socket.on('state_update', async () => {
            try {
                const updated = await api.getGameState(gameCode);
                setGame(updated);
            } catch (e) {
                console.error('Failed to refresh state after socket update', e);
            }
        });
        socket.on('connected', () => { });
        socket.on('joined', () => { });
        socket.on('error', (payload) => { console.warn('Socket error', payload); });

        return () => {
            clearInterval(intervalId);
            if (socketRef.current) {
                socketRef.current.emit('leave_game', { game_code: gameCode });
                socketRef.current.disconnect();
                socketRef.current = null;
            }
        };
    }, [gameCode, navigate]);

    const handleJoinGame = async (playerName) => {
        setLoading(true);
        setError('');
        try {
            const newPlayer = await api.joinGame(gameCode, playerName);
            sessionStorage.setItem(`player_id_${gameCode}`, newPlayer.id);
            setPlayerId(newPlayer.id);
            // Immediately fetch game state to reflect the new player
            const gameState = await api.getGameState(gameCode);
            setGame(gameState);
        } catch (err) {
            console.error("Failed to join game:", err);
            setError(err.message || 'Could not join the game.');
        } finally {
            setLoading(false);
        }
    };

    const handleStorySubmit = async (story) => {
        if (!playerId) return;
        setLoading(true);
        setError('');
        try {
            await api.submitStory(gameCode, playerId, story);
            // The polling will take care of updating the UI
        } catch (err) {
            console.error("Failed to submit story:", err);
            setError(err.message || 'Could not submit your story.');
        } finally {
            setLoading(false);
        }
    }


    if (!game) {
        return (
            <Container>
                <Group position="center" mt="xl">
                    <Loader />
                    <Text>{error ? error : `Loading game ${gameCode}...`}</Text>
                </Group>
            </Container>
        );
    }

    const currentPlayer = game.players.find(p => p.id === playerId);

    return (
        <Container>
            <Title order={1} align="center" mt="md">Game Code: {game.game_code}</Title>
            <Text c="dimmed" size="sm" align="center">Share this code with your friends!</Text>

            <SimpleGrid cols={2} spacing="lg" mt="lg">
                <Paper withBorder shadow="md" p="lg">
                    <Title order={3}>Players ({game.players.length})</Title>
                    <Stack mt="sm">
                        {game.players.map(p => (
                            <Text key={p.id}>
                                {p.name}
                                {p.id === playerId ? ' (You)' : ''}
                                {p.has_submitted_story ? ' ✅' : '...'}
                            </Text>
                        ))}
                        {game.players.length === 0 && <Text c="dimmed">No one has joined yet.</Text>}
                    </Stack>
                </Paper>

                <div>
                    {!currentPlayer && <JoinGameForm onJoin={handleJoinGame} loading={loading} />}
                    {currentPlayer && <PlayerLobby player={currentPlayer} onStorySubmit={handleStorySubmit} loading={loading} />}
                </div>

            </SimpleGrid>

            {error && <Text color="red" mt="md">{error}</Text>}

        </Container>
    );
} 