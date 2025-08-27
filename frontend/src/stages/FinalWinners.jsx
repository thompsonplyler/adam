import { Paper, Title, Text, Group, Badge, Stack, Button } from '@mantine/core';

export default function FinalWinners({ game, onReturn }) {
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
                <Button onClick={() => window.location.reload()}>Play Another</Button>
            </Group>
        </Paper>
    );
}

function deriveWinnersFromPlayers(players) {
    if (!players || players.length === 0) return [];
    const max = Math.max(...players.map(p => p.score || 0));
    return players.filter(p => (p.score || 0) === max).map(p => ({ id: p.id, name: p.name, score: p.score || 0 }));
}


