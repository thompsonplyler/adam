import { useState, useEffect, useRef } from 'react';
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
    const [view, setView] = useState('reading'); // reading, guessing, results
    const [selectedGuess, setSelectedGuess] = useState(null);
    const [results, setResults] = useState(null);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState(null);

    const currentUser = game.players.find(p => p.username === username);
    const isAuthor = game.current_story?.author_id === currentUser?.id;

    // Reset view when a new story comes in
    useEffect(() => {
        setView('reading');
        setResults(null);
        setSelectedGuess(null);
    }, [game.current_story?.id]);

    const handleGuessSubmit = async () => {
        if (!selectedGuess) return;
        setLoading(true);
        setError(null);
        try {
            await api.submitGuess(game.game_code, selectedGuess);
            setView('waiting');
        } catch (err) {
            setError(err.message);
        } finally {
            setLoading(false);
        }
    };

    const handleShowResults = async () => {
        setLoading(true);
        setError(null);
        try {
            const res = await api.getResults(game.game_code);
            setResults(res);
            setView('results');
        } catch (err) {
            setError(err.message);
        } finally {
            setLoading(false);
        }
    };

    if (!game.current_story) {
        return <Text mt="lg">Waiting for the next story...</Text>;
    }

    if (view === 'results') {
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

    if (view === 'waiting') {
        return (
            <Container mt="lg">
                <Text>Guess submitted! Waiting for other players...</Text>
                {/* In a real app, we'd poll or use websockets to know when all guesses are in. */}
                {/* For now, the creator can just advance when ready. */}
                {game.is_creator && <Button onClick={handleShowResults} fullWidth mt="md" loading={loading}>Show Results</Button>}
            </Container>
        )
    }

    return (
        <Container mt="lg">
            <Title order={3}>Who wrote this story?</Title>
            <Paper withBorder p="lg" mt="md" mb="xl">
                <Text fs="italic">"{game.current_story.content}"</Text>
            </Paper>

            {view === 'reading' && <Button fullWidth onClick={() => setView('guessing')}>Ready to Guess</Button>}

            {view === 'guessing' && (
                <>
                    <Title order={4}>Your Guess:</Title>
                    <SimpleGrid cols={2} mt="md">
                        {game.players
                            .filter(p => p.username !== username) // Can't guess yourself
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
                        {isAuthor ? "This is your story, you can't guess!" : "Submit Final Guess"}
                    </Button>
                </>
            )}
            {error && <Text c="red" mt="md">{error}</Text>}
        </Container>
    );
}

export function GameRoom({ gameCode, username, onLeave }) {
    const [game, setGame] = useState(null);
    const [story, setStory] = useState('');
    const [error, setError] = useState(null);
    const [loading, setLoading] = useState(false);
    const pollInterval = useRef(null);

    useEffect(() => {
        const fetchState = async () => {
            try {
                const gameState = await api.getGameState(gameCode);
                setGame(gameState);
            } catch (err) {
                setError(err.message);
            }
        };

        fetchState(); // Initial fetch
        pollInterval.current = setInterval(fetchState, 3000); // Poll every 3 seconds

        return () => clearInterval(pollInterval.current); // Cleanup on component unmount
    }, [gameCode]);

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
            // Polling will pick up the new story
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