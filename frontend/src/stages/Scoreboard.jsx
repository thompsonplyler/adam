import { Paper, Title, Text, Stack, Group, Badge } from '@mantine/core';

export default function Scoreboard({ game }) {
    return (
        <Paper withBorder shadow="xs" p="md" mt="md">
            <Title order={5}>Round results</Title>
            <Text c="dimmed" size="sm">Scores updated. Totals shown below.</Text>
            <Stack mt="xs">
                {game.players.slice().sort((a, b) => b.score - a.score).map(p => (
                    <Group key={p.id} position="apart">
                        <Text>{p.name}</Text>
                        <Badge>{p.score}</Badge>
                    </Group>
                ))}
            </Stack>
        </Paper>
    );
}


