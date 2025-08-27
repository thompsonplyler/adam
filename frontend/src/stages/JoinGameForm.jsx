import { useState } from 'react';
import { Paper, Title, Stack, TextInput, Button } from '@mantine/core';

export default function JoinGameForm({ onJoin, loading }) {
    const [playerName, setPlayerName] = useState('');

    const handleSubmit = (e) => {
        e.preventDefault();
        if (playerName.trim()) {
            onJoin(playerName.trim());
        }
    };

    return (
        <Paper withBorder shadow="md" p="lg" mt="lg">
            <Title order={3}>Join Game</Title>
            <form onSubmit={handleSubmit}>
                <Stack>
                    <TextInput
                        placeholder="Your Name"
                        label="Enter your name to join"
                        required
                        value={playerName}
                        onChange={(e) => setPlayerName(e.currentTarget.value)}
                    />
                    <Button type="submit" loading={loading}>
                        Join
                    </Button>
                </Stack>
            </form>
        </Paper>
    );
}


