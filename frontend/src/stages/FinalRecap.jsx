import { Paper, Title, Text, Stack, Group, Badge } from '@mantine/core';

export default function FinalRecap({ game }) {
    const history = game?.round_history || [];
    const playerById = new Map(game.players.map(p => [p.id, p]));
    return (
        <Paper withBorder shadow="md" p="lg" mt="lg">
            <Title order={3}>Final Recap</Title>
            {history.length === 0 && <Text c="dimmed" mt="xs">No rounds recorded.</Text>}
            <Stack mt="md">
                {history.map((r, idx) => {
                    const author = playerById.get(r.author_id);
                    const correct = (r.correct_guessers || []).map((id) => playerById.get(id)?.name).filter(Boolean);
                    const authorPts = r.author_points_awarded || 0;
                    return (
                        <Paper key={idx} withBorder p="md">
                            <Group position="apart">
                                <Title order={5}>Round {r.round}</Title>
                                <Badge>{author ? `Author: ${author.name}` : 'Author unknown'}</Badge>
                            </Group>
                            <Text mt="xs">Correct guessers: {correct.length ? correct.join(', ') : 'None'}</Text>
                            <Text c="dimmed">Author bonus points: {authorPts}</Text>
                        </Paper>
                    );
                })}
            </Stack>
        </Paper>
    );
}


