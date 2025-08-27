import { Button, Paper, Title, Text, Group } from '@mantine/core';

export default function Guessing({ game, currentPlayer, gameCode, setGame, setError, api }) {
    const isAuthor = game?.current_story?.author_id === currentPlayer?.id;
    const me = game.players.find(pp => pp.id === currentPlayer?.id);
    const hasGuessed = !!me?.has_guessed_current;

    return (
        <Paper withBorder shadow="xs" p="md" mt="md">
            {isAuthor ? (
                <Text c="dimmed">You're the author. Waiting for others to guess…</Text>
            ) : (
                <>
                    <Title order={5}>Who wrote this?</Title>
                    <Group mt="sm">
                        {game.players.filter(p => p.id !== currentPlayer?.id).map(p => (
                            <Button key={p.id}
                                size="xs"
                                variant="light"
                                disabled={hasGuessed}
                                onClick={async () => {
                                    try {
                                        await api.submitGuess(gameCode, currentPlayer.id, p.id);
                                        const updated = await api.getGameState(gameCode);
                                        setGame(updated);
                                    } catch (e) {
                                        setError(e.message || 'Could not submit guess');
                                    }
                                }}>
                                {p.name}
                            </Button>
                        ))}
                    </Group>
                    {hasGuessed && (
                        <Text mt="sm">You guessed!</Text>
                    )}
                    <Text c="dimmed" mt="sm">Guesses: {game.current_story_guess_count} / {Math.max(0, game.players.length - 1)}</Text>
                </>
            )}
        </Paper>
    );
}


