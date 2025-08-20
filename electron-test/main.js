const { app, BrowserWindow } = require('electron');

function createWindow() {
    const win = new BrowserWindow({ width: 1280, height: 800, autoHideMenuBar: true });
    const webUrl = process.env.WEB_URL || 'http://localhost:5173';
    const gameCode = process.env.GAME_CODE || 'ABCD';
    const target = `${webUrl}/game/${gameCode}`;
    console.log('Loading Electron display URL:', target);
    win.loadURL(target);
}

app.whenReady().then(() => {
    createWindow();
    app.on('activate', () => {
        if (BrowserWindow.getAllWindows().length === 0) createWindow();
    });
});
app.on('window-all-closed', () => {
    if (process.platform !== 'darwin') app.quit();
});


