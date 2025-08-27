import { useState } from 'react';
import { Paper, Title, Text, Stack, Textarea, Button } from '@mantine/core';

export default function PlayerLobby({ player, onStorySubmit, loading }) {
    const [story, setStory] = useState('');

    const handleSubmit = (e) => {
        e.preventDefault();
        if (story.trim()) {
            onStorySubmit(story.trim());
        }
    };

    return (
        <Paper withBorder shadow="md" p="lg" mt="lg">
            <Title order={3}>Welcome, {player.name}!</Title>
            <Text c="dimmed">The game will begin once everyone has submitted a story.</Text>

            <form onSubmit={handleSubmit}>
                <Stack mt="md">
                    <Textarea
                        placeholder="Once, I convinced everyone that..."
                        label="Your secret story"
                        required
                        autosize
                        minRows={4}
                        value={story}
                        onChange={(e) => setStory(e.currentTarget.value)}
                        disabled={player.has_submitted_story}
                    />
                    <Button
                        type="submit"
                        loading={loading}
                        disabled={player.has_submitted_story}
                    >
                        {player.has_submitted_story ? "Waiting for others..." : "Submit & Ready Up"}
                    </Button>
                </Stack>
            </form>
        </Paper>
    );
}


