import { Paper, Title, Text } from '@mantine/core';

export default function RoundIntro({ game }) {
    return (
        <Paper withBorder shadow="xs" p="md" mt="md">
            <Title order={5}>Get ready for the next round</Title>
            {game?.current_story && (
                <Text c="dimmed" mt="xs">A new story is up next…</Text>
            )}
        </Paper>
    );
}


