import { useState, useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { Button, Container, Title, Text, Textarea, Stack, Paper, SimpleGrid, Loader, Group } from '@mantine/core';
import * as api from './api';

function LobbyView({ game, username, handleStartGame, handleStorySubmit, story, setStory, loading }) {
    const isCreator = game.is_creator;
    const canStart = game.players.length > 1 && game.players.every(p => p.has_submitted);

    return (
        <>
            <SimpleGrid cols={2} spacing="lg" mt="lg">
                <Paper withBorder shadow="md" p="lg">
                    <Title order={3}>Players ({game.players.length})</Title>
                    <Stack mt="sm">
                        {game.players.map(p => (
                            <Text key={p.id}>
                                {p.username} {p.username === username ? '(You)' : ''}
                                {p.has_submitted ? ' ✅' : '...'}
                            </Text>
                        ))}
                    </Stack>
                </Paper>

                <Paper withBorder shadow="md" p="lg">
                    <Title order={3}>Submit Your Story</Title>
                    <form onSubmit={handleStorySubmit}>
                        <Stack>
                            <Textarea
                                placeholder="Once, I convinced everyone that..."
                                label="Your secret story"
                                required
                                autosize
                                minRows={3}
                                value={story}
                                onChange={(e) => setStory(e.currentTarget.value)}
                                disabled={game.players.find(p => p.username === username)?.has_submitted}
                            />
                            <Button
                                type="submit"
                                loading={loading}
                                disabled={game.players.find(p => p.username === username)?.has_submitted}
                            >
                                Submit Story
                            </Button>
                        </Stack>
                    </form>
                </Paper>
            </SimpleGrid>

            {isCreator && (
                <Button
                    color="green"
                    fullWidth
                    mt="xl"
                    size="lg"
                    onClick={handleStartGame}
                    loading={loading}
                    disabled={!canStart}
                    title={!canStart ? "Waiting for all players to submit their stories..." : "Start the game!"}
                >
                    Start Game
                </Button>
            )}
        </>
    );
}

function InProgressView({ game, username, onNextRound }) {
    const [selectedGuess, setSelectedGuess] = useState(null);
    const [results, setResults] = useState(null);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState(null);

    const currentUser = game.players.find(p => p.username === username);
    const isAuthor = game.current_story?.author_id === currentUser?.id;
    const hasGuessed = game.guessers?.some(g => g.id === currentUser?.id);

    // Reset selected guess when a new story comes in
    useEffect(() => {
        setResults(null);
        setSelectedGuess(null);
    }, [game.current_story?.id]);

    // Fetch results when they are revealed for the current story
    useEffect(() => {
        const fetchResultsIfNeeded = async () => {
            if (game.current_story?.results_revealed && !results) {
                setLoading(true);
                setError(null);
                try {
                    const res = await api.getResults(game.game_code);
                    setResults(res);
                } catch (err) {
                    setError(err.message);
                } finally {
                    setLoading(false);
                }
            }
        };
        fetchResultsIfNeeded();
    }, [game.current_story?.id, game.current_story?.results_revealed, results, game.game_code]);

    const handleGuessSubmit = async () => {
        if (!selectedGuess) return;
        setLoading(true);
        setError(null);
        try {
            await api.submitGuess(game.game_code, selectedGuess);
            // State will now update via polling
        } catch (err) {
            setError(err.message);
        } finally {
            setLoading(false);
        }
    };

    const handleRevealResults = async () => {
        setLoading(true);
        setError(null);
        try {
            // Tell the server to reveal results, polling will update everyone's UI
            await api.revealResults(game.game_code);
        } catch (err) {
            setError(err.message);
        } finally {
            setLoading(false);
        }
    };

    if (!game.current_story) {
        return <Text mt="lg">Waiting for the next story...</Text>;
    }

    // --- VIEW LOGIC ---

    // 1. RESULTS VIEW: If results are revealed, show them.
    if (game.current_story.results_revealed) {
        // Data is being fetched by the useEffect hook
        if (!results) {
            return (
                <Container mt="lg">
                    <Loader style={{ display: 'block', margin: '20px auto' }} />
                    <Text ta="center">Calculating results...</Text>
                </Container>
            );
        }

        return (
            <Container mt="lg">
                <Title order={3}>Round Results!</Title>
                <Text>The author was: <strong>{results.true_author}</strong></Text>
                <Paper withBorder p="lg" mt="md">
                    <Title order={4}>Scores this round:</Title>
                    {Object.entries(results.round_scores).map(([name, score]) => <Text key={name}>{name}: +{score}</Text>)}
                    <Title order={4} mt="md">Total Scores:</Title>
                    {Object.entries(results.total_scores).map(([name, score]) => <Text key={name}>{name}: {score}</Text>)}
                </Paper>
                <Button onClick={onNextRound} fullWidth mt="md">Next Round</Button>
            </Container>
        );
    }

    const allNonAuthors = game.players.filter(p => p.id !== game.current_story.author_id);
    const allGuessesIn = allNonAuthors.length === game.guessers.length;

    // 2. AUTHOR VIEW: If user is the author, show the waiting/spectator view.
    if (isAuthor) {
        const guessers = game.guessers || [];
        const nonAuthorPlayers = game.players.filter(p => p.id !== currentUser.id);
        const waitingForPlayers = nonAuthorPlayers.filter(p => !guessers.find(g => g.id === p.id));

        return (
            <Container mt="lg">
                <Title order={3}>Your story is being guessed!</Title>
                <Paper withBorder p="lg" mt="md" mb="xl">
                    <Text fs="italic">"{game.current_story.content}"</Text>
                </Paper>

                <SimpleGrid cols={2}>
                    <Paper withBorder p="sm">
                        <Text ta="center" fw={700}>Guessed ({guessers.length})</Text>
                        {guessers.map(guesser => <Text key={guesser.id} ta="center">{guesser.username}</Text>)}
                        {guessers.length === 0 && <Text c="dimmed" ta="center">No one yet...</Text>}
                    </Paper>
                    <Paper withBorder p="sm" bg="var(--mantine-color-gray-light)">
                        <Text ta="center" fw={700}>Waiting For ({waitingForPlayers.length})</Text>
                        {waitingForPlayers.map(player => <Text key={player.id} ta="center">{player.username}</Text>)}
                    </Paper>
                </SimpleGrid>

                {allGuessesIn && (
                    <Text ta="center" mt="lg" fw={700}>All guesses are in!</Text>
                )}

                {game.is_creator && allGuessesIn && (
                    <Button onClick={handleRevealResults} fullWidth mt="md" loading={loading}>
                        Show Results
                    </Button>
                )}
            </Container>
        );
    }

    // 3. GUESSER WAITING VIEW: If user has guessed but results aren't revealed.
    if (hasGuessed) {
        return (
            <Container mt="lg">
                <Text>Guess submitted! Waiting for other players...</Text>
                <Loader style={{ display: 'block', margin: '20px auto' }} />
                {game.is_creator && allGuessesIn && (
                    <Button onClick={handleRevealResults} fullWidth mt="md" loading={loading}>
                        Show Results
                    </Button>
                )}
            </Container>
        )
    }

    // 4. GUESSING VIEW: Default view for players who haven't guessed yet.
    return (
        <Container mt="lg">
            <Title order={3}>Who wrote this story?</Title>
            <Paper withBorder p="lg" mt="md" mb="xl">
                <Text fs="italic">"{game.current_story.content}"</Text>
            </Paper>

            <Title order={4}>Your Guess:</Title>
            <SimpleGrid cols={2} mt="md">
                {game.players
                    .filter(p => p.id !== currentUser.id) // Can't guess yourself
                    .map(p => (
                        <Button
                            key={p.id}
                            variant={selectedGuess === p.id ? 'filled' : 'outline'}
                            onClick={() => setSelectedGuess(p.id)}
                            disabled={isAuthor}
                        >
                            {p.username}
                        </Button>
                    ))
                }
            </SimpleGrid>
            <Button onClick={handleGuessSubmit} disabled={!selectedGuess || isAuthor} mt="xl" fullWidth loading={loading}>
                Submit Final Guess
            </Button>
            {error && <Text c="red" mt="md">{error}</Text>}
        </Container>
    );
}

export function GameRoom({ gameCode, username, onLeave }) {
    const [game, setGame] = useState(null);
    const [story, setStory] = useState('');
    const [error, setError] = useState(null);
    const [loading, setLoading] = useState(false);
    const [gameNotFound, setGameNotFound] = useState(false);
    const pollInterval = useRef(null);
    const navigate = useNavigate();

    useEffect(() => {
        const fetchState = async () => {
            try {
                const gameState = await api.getGameState(gameCode);
                setGame(gameState);
            } catch (err) {
                if (err.status === 404) {
                    setGameNotFound(true);
                    clearInterval(pollInterval.current);
                } else {
                    setError(err.message);
                }
            }
        };

        fetchState(); // Initial fetch
        pollInterval.current = setInterval(fetchState, 3000); // Poll every 3 seconds

        return () => clearInterval(pollInterval.current); // Cleanup on component unmount
    }, [gameCode]);

    useEffect(() => {
        if (gameNotFound) {
            const timer = setTimeout(() => {
                navigate('/');
            }, 3000); // Redirect after 3 seconds
            return () => clearTimeout(timer);
        }
    }, [gameNotFound, navigate]);

    if (gameNotFound) {
        return (
            <Container>
                <Title order={2} ta="center" mt="xl">Game Not Found</Title>
                <Text ta="center" mt="md">This game does not exist or has ended.</Text>
                <Text ta="center" mt="sm">Redirecting you to the lobby...</Text>
                <Loader style={{ display: 'block', margin: '20px auto' }} />
            </Container>
        );
    }

    const handleStorySubmit = async (e) => {
        e.preventDefault();
        setLoading(true);
        setError(null);
        try {
            await api.submitStory(game.id, story);
            // The polling will automatically update the UI to show the checkmark
        } catch (err) {
            setError(err.message);
        } finally {
            setLoading(false);
        }
    };

    const handleStartGame = async () => {
        setLoading(true);
        setError(null);
        try {
            await api.startGame(gameCode);
            // Polling will handle the state transition, now also need to fetch first story
            await api.getNextStory(gameCode);
        } catch (err) {
            setError(err.message);
        } finally {
            setLoading(false);
        }
    };

    const handleLeaveGame = async () => {
        const isLastPlayer = game.players.length === 1;
        const confirmationMessage = isLastPlayer
            ? "You are the last player. Leaving will end the game for everyone. Are you sure?"
            : "Are you sure you want to leave the game?";

        if (!window.confirm(confirmationMessage)) return;

        clearInterval(pollInterval.current); // Stop polling immediately

        setLoading(true);
        setError(null);
        try {
            await api.leaveGame(gameCode);
            onLeave();
        } catch (err) {
            setError(err.message);
        } finally {
            setLoading(false);
        }
    }

    const handleNextRound = async () => {
        setLoading(true);
        setError(null);
        try {
            await api.getNextStory(gameCode);
            // Polling will pick up the new story, but let's fetch immediately for responsiveness
            const newState = await api.getGameState(gameCode);
            setGame(newState);
        } catch (err) {
            setError(err.message);
        } finally {
            setLoading(false);
        }
    }

    if (error) return <Text c="red">Error: {error}</Text>;
    if (!game) return <Container><Loader /> <Text>Joining game room...</Text></Container>;

    return (
        <Container>
            <Group justify="space-between">
                <Title>Game Room: {game.game_code}</Title>
                <Button color="red" variant="outline" onClick={handleLeaveGame}>Leave Game</Button>
            </Group>
            <Text>Welcome, {username}!</Text>

            {game.status === 'lobby' && (
                <LobbyView
                    game={game}
                    username={username}
                    handleStartGame={handleStartGame}
                    handleStorySubmit={handleStorySubmit}
                    story={story}
                    setStory={setStory}
                    loading={loading}
                />
            )}

            {game.status === 'in_progress' && (
                <InProgressView game={game} username={username} onNextRound={handleNextRound} />
            )}

            {game.status === 'finished' && <Title>Game Over!</Title>}
        </Container>
    );
} 