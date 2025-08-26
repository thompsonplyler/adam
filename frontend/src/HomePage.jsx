import React, { useState } from 'react';
import { Button, Container, Title, Stack, TextInput, Group } from '@mantine/core';
import { useNavigate } from 'react-router-dom';

function HomePage() {
    const navigate = useNavigate();
    const [code, setCode] = useState('');

    const handleJoin = (e) => {
        e?.preventDefault?.();
        const trimmed = (code || '').toString().trim().toUpperCase();
        if (trimmed.length >= 4) {
            navigate(`/game/${trimmed}`);
        }
    };

    return (
        <Container size="xs" style={{ paddingTop: '50px' }}>
            <Stack align="center" gap="md">
                <Title order={1}>It Wasn't Me</Title>
                <form onSubmit={handleJoin} style={{ width: '100%' }}>
                    <Stack>
                        <TextInput
                            label="Enter game code"
                            placeholder="ABCD"
                            value={code}
                            onChange={(e) => setCode(e.currentTarget.value)}
                        />
                        <Group justify="center">
                            <Button type="submit" size="md">
                                Join Game
                            </Button>
                        </Group>
                    </Stack>
                </form>
            </Stack>
        </Container>
    );
}

export default HomePage; 