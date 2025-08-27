import { Paper, Title, Text, Group, Badge, Stack, Button, Progress } from '@mantine/core';
import { useNavigate } from 'react-router-dom';
import * as api from '../api';
import { useEffect, useState } from 'react';

export default function FinalWinners({ game, onReturn }) {
    const navigate = useNavigate();
    const [votes, setVotes] = useState(game?.replay_votes || 0);
    useEffect(() => {
        setVotes(game?.replay_votes || 0);
    }, [game?.replay_votes]);
    const winners = game?.winners && game.winners.length
        ? game.winners
        : deriveWinnersFromPlayers(game?.players || []);
    const plural = winners.length > 1;
    return (
        <Paper withBorder shadow="md" p="lg" mt="lg">
            <Title order={3}>{plural ? 'Winners' : 'Winner'}</Title>
            <Stack mt="sm">
                {winners.map(w => (
                    <Group key={w.id} position="apart">
                        <Text>{w.name}</Text>
                        <Badge>{w.score ?? 0}</Badge>
                    </Group>
                ))}
            </Stack>
            <Group mt="md">
                <Button variant="outline" onClick={onReturn}>Return to Main Menu</Button>
                <Button onClick={async () => {
                    try {
                        const pid = sessionStorage.getItem(`player_id_${game.game_code}`);
                        await api.voteReplay(game.game_code, Number(pid));
                    } catch { }
                }}>Replay?</Button>
            </Group>
            <Group mt="sm">
                <Text c="dimmed" size="sm">Replay votes</Text>
                <Progress value={Math.min(100, (votes / Math.max(1, game.players.length)) * 100)} w={200} />
                <Badge>{votes}/{game.players.length}</Badge>
            </Group>
        </Paper>
    );
}

function deriveWinnersFromPlayers(players) {
    if (!players || players.length === 0) return [];
    const max = Math.max(...players.map(p => p.score || 0));
    return players.filter(p => (p.score || 0) === max).map(p => ({ id: p.id, name: p.name, score: p.score || 0 }));
}


