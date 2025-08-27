import { Paper, Title, Text, List } from '@mantine/core';

export default function Scoreboard({ state }: { state: any }) {
    return (
        <Paper withBorder p="md" mt="md">
            <Title order={5}>Round results</Title>
            <Text c="dimmed" size="sm">Scores updated. Totals shown below.</Text>
            <List mt="xs">
                {state?.players?.slice().sort((a: any, b: any) => (b.score || 0) - (a.score || 0)).map((p: any) => (
                    <List.Item key={p.id}>{p.name}: {p.score ?? 0}</List.Item>
                ))}
            </List>
        </Paper>
    );
}


