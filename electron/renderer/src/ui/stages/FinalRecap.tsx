import { Paper, Title, Text, List, Group, Badge } from '@mantine/core';

export default function FinalRecap({ state }: { state: any }) {
    const history = state?.round_history || [];
    const players = new Map((state?.players || []).map((p: any) => [p.id, p]));
    return (
        <Paper withBorder p="md" mt="md">
            <Title order={4}>Final Recap</Title>
            {history.length === 0 && <Text c="dimmed" mt="xs">No rounds recorded.</Text>}
            <List mt="sm">
                {history.map((r: any, idx: number) => (
                    <List.Item key={idx}>
                        <Group justify="space-between">
                            <Text>Round {r.round}</Text>
                            <Badge>{players.get(r.author_id)?.name ? `Author: ${players.get(r.author_id).name}` : 'Author unknown'}</Badge>
                        </Group>
                        <Text c="dimmed">Correct guessers: {(r.correct_guessers || []).map((id: number) => players.get(id)?.name).filter(Boolean).join(', ') || 'None'}</Text>
                        <Text c="dimmed">Author bonus points: {r.author_points_awarded || 0}</Text>
                    </List.Item>
                ))}
            </List>
        </Paper>
    );
}


