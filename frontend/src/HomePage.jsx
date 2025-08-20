import React from 'react';
import { Button, Container, Title, Stack } from '@mantine/core';
import { useNavigate } from 'react-router-dom';
import { createGame } from './api';

function HomePage() {
    const navigate = useNavigate();

    const handleCreateGame = async () => {
        try {
            const newGame = await createGame();
            if (newGame && newGame.game_code) {
                navigate(`/game/${newGame.game_code}`);
            }
        } catch (error) {
            console.error("Failed to create game:", error);
            // We can add user-facing error handling here later
        }
    };

    return (
        <Container size="xs" style={{ paddingTop: '50px' }}>
            <Stack align="center">
                <Title order={1}>It Wasn't Me</Title>
                <Button onClick={handleCreateGame} size="lg">
                    Create Game
                </Button>
            </Stack>
        </Container>
    );
}

export default HomePage; 