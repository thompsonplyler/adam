import { Paper, Title, Text } from '@mantine/core';

export default function Guessing({ state }: { state: any }) {
    const totalGuessers = Math.max(0, (state?.players?.length ?? 1) - 1);
    return (
        <Paper withBorder p="md" mt="md">
            <Title order={5}>Players are guessing…</Title>
            <Text c="dimmed" mt="sm">Guesses: {state?.current_story_guess_count ?? 0} / {totalGuessers}</Text>
        </Paper>
    );
}


