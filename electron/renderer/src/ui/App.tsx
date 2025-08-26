import { useEffect, useState } from 'react';
import { Container, Title, Text, Group, Badge, Button, Stack, Paper, Divider, CopyButton, Tooltip, ActionIcon, List } from '@mantine/core';
import { io, Socket } from 'socket.io-client';
import { createGame, getGameState, type GameState } from '../lib/api';

export function App() {
    const [socket, setSocket] = useState<Socket | null>(null);
    const [connected, setConnected] = useState(false);
    const [room, setRoom] = useState('');
    const [gameCode, setGameCode] = useState<string>(() => localStorage.getItem('game_code') || '');
    const [creating, setCreating] = useState(false);
    const [state, setState] = useState<GameState | null>(null);
    const [deadline, setDeadline] = useState<number | null>(null);
    const [nowTs, setNowTs] = useState<number>(Date.now());
    const [apiError, setApiError] = useState<string | null>(null);

    useEffect(() => {
        const baseUrl = (import.meta as any).env.VITE_API_URL || (globalThis as any).process?.env?.API_URL || 'http://localhost:5000';
        const s = io(baseUrl + '/ws');
        setSocket(s);
        ; (window as any).__hostSocket = s;
        s.on('connect', () => {
            setConnected(true);
            if (gameCode) s.emit('join_game', { game_code: gameCode, is_session_owner: true });
        });
        s.on('joined', (m: any) => setRoom(m?.room ?? ''));
        s.on('state_update', async () => {
            if (gameCode) {
                try {
                    const st = await getGameState(gameCode);
                    setState(st);
                    try { setDeadline(Date.now() + ((st?.durations?.[st?.stage as any] || 0) * 1000)); } catch { }
                } catch { /* ignore */ }
            }
        });
        s.on('session_ended', () => {
            // If we receive this as host, reset UI to Start Game
            localStorage.removeItem('game_code');
            setGameCode('');
            setState(null);
            setRoom('');
        });
        return () => { s.disconnect(); };
    }, [gameCode]);

    // Tick timer for countdown every 500ms
    useEffect(() => {
        const id = setInterval(() => setNowTs(Date.now()), 500);
        return () => clearInterval(id);
    }, []);

    useEffect(() => {
        if (!gameCode) return;
        localStorage.setItem('game_code', gameCode);
        getGameState(gameCode).then(setState).catch(() => setState(null));
    }, [gameCode]);

    const handleCreate = async () => {
        setCreating(true); setApiError(null);
        try {
            const res = await createGame();
            setGameCode(res.game_code);
            if (socket) socket.emit('join_game', { game_code: res.game_code, is_session_owner: true });
        } catch (e: any) {
            setApiError(e?.message || 'Failed to create game');
        } finally {
            setCreating(false);
        }
    };

    const handleQuit = () => {
        try {
            if (socket && gameCode) socket.emit('leave_game', { game_code: gameCode });
        } catch { }
        localStorage.removeItem('game_code');
        setGameCode('');
        setState(null);
        setRoom('');
    };

    const isInProgress = state?.status === 'in_progress';
    const isFinished = state?.status === 'finished';
    const remainingMs = deadline ? Math.max(0, deadline - nowTs) : 0;
    const remainingSec = Math.ceil(remainingMs / 1000);

    return (
        <Container>
            <Group justify="space-between" mt="md">
                <Title order={2}>It Wasn't Me — Display</Title>
                <Badge color={connected ? 'green' : 'red'}>{connected ? 'Connected' : 'Disconnected'}</Badge>
            </Group>
            <Paper withBorder p="md" mt="md">
                <Stack>
                    <Group>
                        <Button onClick={handleCreate} loading={creating}>Start Game</Button>
                        {gameCode && (
                            <Group>
                                <Text>Game Code:</Text>
                                <CopyButton value={gameCode} timeout={1000}>
                                    {({ copied, copy }) => (
                                        <Tooltip label={copied ? 'Copied' : 'Copy'}>
                                            <ActionIcon onClick={copy} variant="light">{gameCode}</ActionIcon>
                                        </Tooltip>
                                    )}
                                </CopyButton>
                                <Button variant="light" color="red" onClick={handleQuit}>Quit Lobby</Button>
                            </Group>
                        )}
                    </Group>
                    {apiError && <Text c="red">{apiError}</Text>}
                </Stack>
            </Paper>
            {gameCode && (
                <Paper withBorder p="md" mt="md">
                    <Group justify="space-between">
                        <Title order={4}>Players ({state?.players.length ?? 0})</Title>
                        <Group>
                            {state && (
                                <Badge color={isFinished ? 'red' : (isInProgress ? 'blue' : 'yellow')}>
                                    {isFinished ? 'Finished' : (isInProgress ? 'In Progress' : 'Lobby')}
                                </Badge>
                            )}
                            {isInProgress && (
                                <Badge color="grape">{state?.stage === 'scoreboard' ? 'Scoreboard' : (state?.stage === 'guessing' ? 'Guessing' : 'Round intro')}</Badge>
                            )}
                            <Text c="dimmed">Room: {room || '(joining...)'}</Text>
                        </Group>
                    </Group>
                    <Divider my="sm" />
                    {state?.players?.length ? (
                        <List>
                            {state.players.map(p => (
                                <List.Item key={p.id}>{p.name} {p.has_submitted_story ? '✅' : '...'}</List.Item>
                            ))}
                        </List>
                    ) : (
                        <Text c="dimmed">Waiting for players...</Text>
                    )}
                </Paper>
            )}
            {isInProgress && (
                <Paper withBorder p="md" mt="md">
                    <Group justify="space-between">
                        <Title order={4}>Round {state?.current_round} of {state?.total_rounds}</Title>
                        <Badge>{state?.stage === 'scoreboard' ? 'Scoreboard' : (state?.stage === 'guessing' ? 'Guessing' : 'Round intro')}</Badge>
                    </Group>
                    <Text c="dimmed" mt="xs">
                        {state?.stage === 'scoreboard' ? 'Reviewing scores...' : (state?.stage === 'guessing' ? 'Players are guessing…' : 'Get ready for the next round.')}
                    </Text>
                    {state?.status === 'in_progress' && (
                        <Text c="dimmed" size="sm" mt="xs">Auto-advances in {remainingSec}s</Text>
                    )}
                    {state?.current_story && (
                        <Paper withBorder p="md" mt="md">
                            <Title order={5}>Current Story</Title>
                            <Text mt="xs">{state.current_story.content}</Text>
                            {state?.stage === 'guessing' && (
                                <Text c="dimmed" mt="sm">Guesses: {state?.current_story_guess_count ?? 0} / {(state?.players?.length ?? 1) - 1}</Text>
                            )}
                        </Paper>
                    )}
                    {state?.stage === 'scoreboard' && (
                        <Paper withBorder p="md" mt="md">
                            <Title order={5}>Round results</Title>
                            <Text c="dimmed" size="sm">Scores updated. Totals shown below.</Text>
                            <List mt="xs">
                                {state?.players?.slice().sort((a: any, b: any) => (b.score || 0) - (a.score || 0)).map((p: any) => (
                                    <List.Item key={p.id}>{p.name}: {p.score ?? 0}</List.Item>
                                ))}
                            </List>
                        </Paper>
                    )}
                </Paper>
            )}
            {isFinished && (
                <Paper withBorder p="md" mt="md">
                    <Title order={3}>Game finished</Title>
                    <Text c="dimmed">Thanks for playing!</Text>
                </Paper>
            )}
        </Container>
    );
}


