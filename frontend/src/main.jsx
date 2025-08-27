import React from 'react'
import ReactDOM from 'react-dom/client'
import { MantineProvider } from '@mantine/core'
import App from './App'
import './index.css'
import '@mantine/core/styles.css'
import { appTheme } from './theme'

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <MantineProvider theme={appTheme}>
      <App />
    </MantineProvider>
  </React.StrictMode>,
)
