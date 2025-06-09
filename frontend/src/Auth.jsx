import { useState } from 'react';
import { useForm } from '@mantine/form';
import { Button, TextInput, Paper, Title, Container, Stack } from '@mantine/core';
import { login, register } from './api';

export function Auth({ onLogin }) {
    const [isRegister, setIsRegister] = useState(false);
    const [error, setError] = useState(null);

    const form = useForm({
        initialValues: {
            username: '',
            password: '',
        },
        validate: {
            username: (value) => (value.length < 3 ? 'Username must have at least 3 letters' : null),
            password: (value) => (value.length < 6 ? 'Password must have at least 6 letters' : null),
        },
    });

    const handleSubmit = async (values) => {
        setError(null);
        try {
            const action = isRegister ? register : login;
            await action(values.username, values.password);
            // If login/register is successful, call the onLogin callback
            onLogin(values.username);
        } catch (err) {
            setError(err.message);
        }
    };

    return (
        <Container size={420} my={40}>
            <Title ta="center">It Wasn't Me</Title>
            <Paper withBorder shadow="md" p={30} mt={30} radius="md">
                <form onSubmit={form.onSubmit(handleSubmit)}>
                    <Stack>
                        <TextInput
                            required
                            label="Username"
                            placeholder="Your username"
                            {...form.getInputProps('username')}
                        />
                        <TextInput
                            required
                            label="Password"
                            type="password"
                            placeholder="Your password"
                            {...form.getInputProps('password')}
                        />
                        <Button type="submit">{isRegister ? 'Register' : 'Login'}</Button>
                    </Stack>
                </form>
                <Button variant="subtle" fullWidth mt="md" onClick={() => setIsRegister(!isRegister)}>
                    {isRegister ? 'Already have an account? Login' : "Don't have an account? Register"}
                </Button>
                {error && <p style={{ color: 'red', textAlign: 'center' }}>{error}</p>}
            </Paper>
        </Container>
    );
} 