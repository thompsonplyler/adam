import { Paper, Title, Text, Stack, Group, Badge } from '@mantine/core';

export default function Scoreboard({ game }) {
    const authorName = game?.current_story ? (game.players.find(p => p.id === game.current_story.author_id)?.name || 'Unknown') : null;
    return (
        <Paper withBorder shadow="xs" p="md" mt="md">
            <Title order={5}>Round results</Title>
            {authorName && (
                <Text mt="xs"><strong>Author:</strong> {authorName}</Text>
            )}
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


