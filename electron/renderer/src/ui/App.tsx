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
    const [apiError, setApiError] = useState<string | null>(null);

    useEffect(() => {
        const baseUrl = (import.meta as any).env.VITE_API_URL || (globalThis as any).process?.env?.API_URL || 'http://localhost:5000';
        const s = io(baseUrl + '/ws');
        setSocket(s);
        s.on('connect', () => {
            setConnected(true);
            if (gameCode) s.emit('join_game', { game_code: gameCode });
        });
        s.on('joined', (m: any) => setRoom(m?.room ?? ''));
        s.on('state_update', async () => {
            if (gameCode) {
                try { setState(await getGameState(gameCode)); } catch { /* ignore */ }
            }
        });
        return () => { s.disconnect(); };
    }, [gameCode]);

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
            if (socket) socket.emit('join_game', { game_code: res.game_code });
        } catch (e: any) {
            setApiError(e?.message || 'Failed to create game');
        } finally {
            setCreating(false);
        }
    };

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
                        <Text c="dimmed">Room: {room || '(joining...)'}</Text>
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
        </Container>
    );
}


