// Use CommonJS require for Electron to avoid ESM interop issues in dev
// eslint-disable-next-line @typescript-eslint/no-var-requires
const { app, BrowserWindow } = require('electron');
import type { Event } from 'electron';

let mainWindow: InstanceType<typeof BrowserWindow> | null = null;

function createWindow() {
    console.log('[main] createWindow called');
    mainWindow = new BrowserWindow({
        width: 1280,
        height: 800,
        autoHideMenuBar: true,
    });
    const rendererUrl = process.env.RENDERER_URL || 'http://localhost:5174';
    console.log('[main] loading URL:', rendererUrl);
    mainWindow.loadURL(rendererUrl).catch((err: unknown) => {
        console.error('[main] loadURL error:', err);
    });
    // Open devtools to inspect renderer errors during dev
    try {
        mainWindow.webContents.openDevTools({ mode: 'detach' } as any);
    } catch { }
    // Log load status
    mainWindow.webContents.on('did-finish-load', () => {
        console.log('[main] renderer did-finish-load');
    });
    mainWindow.webContents.on('did-fail-load', (_e: Event, errorCode: number, errorDescription: string) => {
        console.error('[main] renderer did-fail-load', errorCode, errorDescription);
    });
}

app.whenReady().then(() => {
    console.log('[main] app ready');
    createWindow();
    app.on('activate', () => {
        console.log('[main] app activate');
        if (BrowserWindow.getAllWindows().length === 0) {
            createWindow();
        }
    });
});

app.on('window-all-closed', () => {
    if (process.platform !== 'darwin') app.quit();
});

// Best-effort signal to end session when the app quits
app.on('before-quit', () => {
    try {
        // Inject a small script into the renderer to emit leave if we have a code
        if (mainWindow) {
            mainWindow.webContents.executeJavaScript(`
                try {
                  const code = localStorage.getItem('game_code');
                  if (code && window.__hostSocket) {
                    window.__hostSocket.emit('leave_game', { game_code: code });
                  }
                } catch {}
            `);
        }
    } catch { }
});


