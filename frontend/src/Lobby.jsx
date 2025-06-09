import { useState, useEffect } from 'react';
import { Button, TextInput, Paper, Title, Container, Stack, Group } from '@mantine/core';
import { useNavigate } from 'react-router-dom';
import { createGame, joinGame, getActiveGames } from './api';

export function Lobby({ username, onLogout }) {
    const [joinCode, setJoinCode] = useState('');
    const [activeGames, setActiveGames] = useState([]);
    const [error, setError] = useState(null);
    const navigate = useNavigate();

    useEffect(() => {
        const checkForActiveGame = async () => {
            try {
                const games = await getActiveGames();
                setActiveGames(games);
            } catch (err) {
                console.error("Could not check for active games:", err);
                // If we get a 401, the session might be expired, so log out.
                if (err.message.includes('401')) {
                    onLogout();
                }
                setError('Could not fetch active games.');
            }
        };
        checkForActiveGame();
    }, [onLogout]);

    const handleCreateGame = async () => {
        setError(null);
        try {
            const newGame = await createGame();
            navigate(`/game/${newGame.code}`);
        } catch {
            setError('Could not create game.');
        }
    };

    const handleJoinGame = async (e) => {
        e.preventDefault();
        setError(null);
        try {
            await joinGame(joinCode);
            navigate(`/game/${joinCode}`);
        } catch {
            setError('Could not join game. Check the code and try again.');
        }
    };

    return (
        <Container size={420} my={40}>
            <Group justify="space-between">
                <Title ta="center">Welcome, {username}!</Title>
                <Button onClick={onLogout}>Logout</Button>
            </Group>

            {error && <p style={{ color: 'red' }}>{error}</p>}

            {activeGames.length > 0 && (
                <Paper withBorder shadow="md" p={30} mt={30} radius="md">
                    <Title order={3} ta="center" mb="md">Your Active Games</Title>
                    <Stack>
                        {activeGames.map(game => (
                            <Button key={game.game_code} onClick={() => navigate(`/game/${game.game_code}`)}>
                                Rejoin Game: {game.game_code}
                            </Button>
                        ))}
                    </Stack>
                </Paper>
            )}

            <Paper withBorder shadow="md" p={30} mt={30} radius="md">
                <Stack>
                    <Button onClick={handleCreateGame}>Create New Game</Button>
                    <form onSubmit={handleJoinGame}>
                        <TextInput
                            label="Join Existing Game"
                            placeholder="Enter game code"
                            value={joinCode}
                            onChange={(event) => setJoinCode(event.currentTarget.value)}
                            required
                        />
                        <Button type="submit" fullWidth mt="md">
                            Join Game
                        </Button>
                    </form>
                </Stack>
            </Paper>
        </Container>
    );
} 