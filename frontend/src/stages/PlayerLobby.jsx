import { useState } from 'react';
import { Paper, Stack, Textarea, Button, Group, Text } from '@mantine/core';

export default function PlayerLobby({ player, onStorySubmit, loading, requiredCount = 1 }) {
    const [story, setStory] = useState('');
    const [submitted, setSubmitted] = useState(0);

    const handleSubmit = (e) => {
        e.preventDefault();
        if (story.trim()) {
            onStorySubmit(story.trim());
        }
    };

    return (
        <Paper withBorder shadow="md" p="lg" mt="lg">
            <form onSubmit={(e) => { e.preventDefault(); if (story.trim()) { onStorySubmit(story.trim()); setStory(''); setSubmitted((s) => Math.min(requiredCount, s + 1)); } }}>
                <Stack>
                    <Textarea
                        placeholder="Once, I convinced everyone that..."
                        label="Your secret story"
                        required
                        autosize
                        minRows={4}
                        value={story}
                        onChange={(e) => setStory(e.currentTarget.value)}
                        disabled={player.has_submitted_story || submitted >= requiredCount}
                    />
                    <Button
                        type="submit"
                        loading={loading}
                        disabled={player.has_submitted_story || submitted >= requiredCount}
                    >
                        {player.has_submitted_story ? "Waiting for others..." : (submitted >= requiredCount ? "All submitted" : "Submit & Ready Up")}
                    </Button>
                    <Group justify="space-between">
                        <Text c="dimmed" size="sm">Submitted: {submitted}/{requiredCount}</Text>
                    </Group>
                </Stack>
            </form>
        </Paper>
    );
}


