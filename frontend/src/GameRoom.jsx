import { useState, useEffect, useRef } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { Button, Container, Title, Text, Paper, SimpleGrid, Loader, Group, Stack, Badge } from '@mantine/core';
import * as api from './api';
import { io } from 'socket.io-client';
import RoundIntro from './stages/RoundIntro';
import Guessing from './stages/Guessing';
import Scoreboard from './stages/Scoreboard';
import JoinGameForm from './stages/JoinGameForm';
import PlayerLobby from './stages/PlayerLobby';
import FinalWinners from './stages/FinalWinners';

// Lobby components moved to ./stages


export function GameRoom() {
    const { gameCode } = useParams();
    const navigate = useNavigate();
    const [game, setGame] = useState(null);
    const [deadline, setDeadline] = useState(null);
    const [nowTs, setNowTs] = useState(Date.now());
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
                // initialize deadline from server if present
                try {
                    if (gameState?.stage_deadline) {
                        setDeadline(Math.floor(gameState.stage_deadline * 1000));
                    } else if (gameState?.durations && gameState?.stage) {
                        setDeadline(Date.now() + ((gameState.durations[gameState.stage] || 0) * 1000));
                    }
                } catch { }
                // Do not clear error automatically; keep it visible until next user action
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
                // prefer server deadline when available, else fallback to durations map
                try {
                    if (updated?.stage_deadline) {
                        setDeadline(Math.floor(updated.stage_deadline * 1000));
                    } else {
                        setDeadline(Date.now() + ((updated?.durations?.[updated?.stage] || 0) * 1000));
                    }
                } catch { }
            } catch (e) {
                console.error('Failed to refresh state after socket update', e);
            }
        });
        socket.on('session_ended', () => {
            setError('Session ended');
            // Clear any stored player id for this code
            try { sessionStorage.removeItem(`player_id_${gameCode}`); } catch { }
            navigate('/');
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

    // Tick timer to refresh countdown every 500ms
    useEffect(() => {
        const id = setInterval(() => setNowTs(Date.now()), 500);
        return () => clearInterval(id);
    }, []);

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
    const controllerId = game.players.length ? Math.min(...game.players.map(p => p.id)) : null;
    const isController = currentPlayer && controllerId === currentPlayer.id;
    const allReady = game.players.length > 0 && game.players.every(p => p.has_submitted_story);
    const isInProgress = game.status === 'in_progress';
    const remainingMs = deadline ? Math.max(0, deadline - nowTs) : 0;
    const remainingSec = Math.ceil(remainingMs / 1000);
    const isFinished = game.status === 'finished';

    if (isFinished) {
        return (
            <Container>
                <Title order={1} align="center" mt="md">Game Code: {game.game_code}</Title>
                <Group position="center" mt="xs">
                    <Badge color='red'>Finished</Badge>
                </Group>
                <FinalWinners game={game} onReturn={() => navigate('/')} />
                {error && <Text color="red" mt="md">{error}</Text>}
            </Container>
        );
    }

    return (
        <Container>
            <Title order={1} align="center" mt="md">Game Code: {game.game_code}</Title>
            <Group position="center" mt="xs">
                {currentPlayer && <Badge color={isController ? 'green' : 'gray'}>{isController ? 'Controller' : 'Player'}</Badge>}
                <Badge color={isFinished ? 'red' : (isInProgress ? 'blue' : 'yellow')}>
                    {isFinished ? 'Finished' : (isInProgress ? 'In Progress' : 'Lobby')}
                </Badge>
                {isInProgress && (
                    <Badge color="grape">{game.stage === 'scoreboard' ? 'Scoreboard' : (game.stage === 'guessing' ? 'Guessing' : 'Round intro')}</Badge>
                )}
                {game.status === 'lobby' && <Text c="dimmed" size="sm">{allReady ? 'Everyone is ready' : 'Waiting for all players to be ready'}</Text>}
            </Group>

            <SimpleGrid cols={2} spacing="lg" mt="lg">
                {!isFinished && (
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
                )}

                <div>
                    {game.status === 'lobby' && !currentPlayer && <JoinGameForm onJoin={handleJoinGame} loading={loading} />}
                    {game.status === 'lobby' && currentPlayer && <PlayerLobby player={currentPlayer} onStorySubmit={handleStorySubmit} loading={loading} />}
                    {game.status === 'lobby' && currentPlayer && isController && allReady && (
                        <Button mt="md" onClick={async () => {
                            try {
                                setError('');
                                await api.startGame(gameCode, currentPlayer.id);
                                const updated = await api.getGameState(gameCode);
                                setGame(updated);
                            } catch (e) {
                                setError(e.message || 'Could not start game');
                            }
                        }}>Start Game</Button>
                    )}
                    {isInProgress && (
                        <Paper withBorder shadow="md" p="lg" mt="lg">
                            <Group position="apart">
                                <Title order={3}>Round {game.current_round} of {game.total_rounds}</Title>
                                <Badge>{game.stage === 'scoreboard' ? 'Scoreboard' : (game.stage === 'guessing' ? 'Guessing' : 'Round intro')}</Badge>
                            </Group>
                            <Text c="dimmed" mt="xs">
                                {game.stage === 'scoreboard' ? 'Reviewing scores...' : (game.stage === 'guessing' ? 'Make your guess!' : 'Get ready for the next round.')}
                            </Text>
                            {game.stage !== 'finished' && game.status === 'in_progress' && (
                                <Text c="dimmed" size="sm" mt="xs">Auto-advances in {remainingSec}s</Text>
                            )}
                            {game.current_story && (
                                <Paper withBorder shadow="xs" p="md" mt="md">
                                    <Title order={5}>Current Story</Title>
                                    <Text mt="xs">{game.current_story.content}</Text>
                                </Paper>
                            )}
                            {game.stage === 'round_intro' && (
                                <RoundIntro game={game} />
                            )}
                            {game.stage === 'guessing' && currentPlayer && game.current_story && (
                                <Guessing game={game} currentPlayer={currentPlayer} gameCode={gameCode} setGame={setGame} setError={setError} api={api} />
                            )}
                            {game.stage === 'scoreboard' && (
                                <Scoreboard game={game} />
                            )}
                            {isController && (
                                <Button mt="md" onClick={async () => {
                                    try {
                                        await api.advanceRound(gameCode, currentPlayer.id);
                                        const updated = await api.getGameState(gameCode);
                                        setGame(updated);
                                    } catch (e) {
                                        setError(e.message || 'Could not advance');
                                    }
                                }}>Next</Button>
                            )}
                        </Paper>
                    )}
                    {/* Final screen handled by early return; nothing else renders when finished */}
                </div>

            </SimpleGrid>

            {error && <Text color="red" mt="md">{error}</Text>}

        </Container>
    );
} 