import React from 'react';
import ReactDOM from 'react-dom/client';
import { MantineProvider } from '@mantine/core';
import '@mantine/core/styles.css';
import { appTheme } from '../../../shared/theme';
import { App } from './ui/App';

ReactDOM.createRoot(document.getElementById('root')!).render(
    <React.StrictMode>
        <MantineProvider theme={appTheme}>
            <App />
        </MantineProvider>
    </React.StrictMode>
);


