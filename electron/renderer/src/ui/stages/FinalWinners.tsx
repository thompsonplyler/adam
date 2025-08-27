import { Paper, Title, Text, Group, Badge, Stack, Button } from '@mantine/core';
import { startReplay } from '../../lib/api';

export default function FinalWinners({ state }: { state: any }) {
    const winners = (state?.winners && state.winners.length)
        ? state.winners
        : deriveWinnersFromPlayers(state?.players || []);
    const plural = winners.length > 1;
    return (
        <Paper withBorder p="md" mt="md">
            <Title order={3}>{plural ? 'Winners' : 'Winner'}</Title>
            <Stack mt="sm">
                {winners.map((w: any) => (
                    <Group key={w.id} justify="space-between">
                        <Text>{w.name}</Text>
                        <Badge>{w.score ?? 0}</Badge>
                    </Group>
                ))}
            </Stack>
            <Group mt="md">
                <Button onClick={async () => {
                    try {
                        const controllerId = Math.min(...(state?.players || []).map((p: any) => p.id));
                        await startReplay(state?.game_code, controllerId);
                    } catch { }
                }}>Start Replay</Button>
            </Group>
        </Paper>
    );
}

function deriveWinnersFromPlayers(players: any[]) {
    if (!players || players.length === 0) return [] as any[];
    const max = Math.max(...players.map(p => p.score || 0));
    return players.filter(p => (p.score || 0) === max).map(p => ({ id: p.id, name: p.name, score: p.score || 0 }));
}


