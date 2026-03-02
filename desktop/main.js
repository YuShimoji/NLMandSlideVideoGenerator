const { app, BrowserWindow, dialog } = require('electron');
const path = require('path');
const { spawn } = require('child_process');
const http = require('http');

// ─── Configuration ───────────────────────────────────────────
const STREAMLIT_PORT = 8501;
const SERVER_STARTUP_TIMEOUT_MS = 45000;
const POLL_INTERVAL_MS = 500;

// ─── Resolve project paths ──────────────────────────────────
function resolveProjectRoot() {
    // In packaged app: resources/app.asar → go up to resources, then find extraResources
    if (app.isPackaged) {
        return path.join(process.resourcesPath);
    }
    // In development: desktop/ → project root
    return path.join(__dirname, '..');
}

function resolvePythonPaths() {
    const root = resolveProjectRoot();

    if (app.isPackaged) {
        // Packaged: venv is in extraResources
        return {
            projectRoot: root,
            python: path.join(root, 'venv', 'Scripts', 'python.exe'),
            streamlit: path.join(root, 'venv', 'Scripts', 'streamlit.exe'),
            webApp: path.join(root, 'src', 'web', 'web_app.py'),
        };
    }

    // Development: use venv in project root
    const projectRoot = path.join(__dirname, '..');
    return {
        projectRoot,
        python: path.join(projectRoot, 'venv', 'Scripts', 'python.exe'),
        streamlit: path.join(projectRoot, 'venv', 'Scripts', 'streamlit.exe'),
        webApp: path.join(projectRoot, 'src', 'web', 'web_app.py'),
    };
}

// ─── Globals ─────────────────────────────────────────────────
let mainWindow = null;
let splashWindow = null;
let serverProcess = null;

// ─── Splash Screen ──────────────────────────────────────────
function createSplashWindow() {
    splashWindow = new BrowserWindow({
        width: 480,
        height: 320,
        frame: false,
        transparent: true,
        alwaysOnTop: true,
        resizable: false,
        webPreferences: {
            nodeIntegration: false,
            contextIsolation: true,
        },
    });

    splashWindow.loadFile(path.join(__dirname, 'splash.html'));
    splashWindow.center();
}

// ─── Main Window ────────────────────────────────────────────
function createMainWindow() {
    mainWindow = new BrowserWindow({
        width: 1400,
        height: 900,
        minWidth: 1024,
        minHeight: 700,
        title: 'NLM Slide Video Generator',
        icon: path.join(__dirname, 'build', 'icon.ico'),
        show: false,
        webPreferences: {
            nodeIntegration: false,
            contextIsolation: true,
            preload: path.join(__dirname, 'preload.js'),
        },
    });

    mainWindow.loadURL(`http://localhost:${STREAMLIT_PORT}`);

    mainWindow.once('ready-to-show', () => {
        if (splashWindow) {
            splashWindow.close();
            splashWindow = null;
        }
        mainWindow.show();
        mainWindow.focus();
    });

    mainWindow.on('closed', () => {
        mainWindow = null;
    });

    // Remove menu bar for cleaner look
    mainWindow.setMenuBarVisibility(false);
}

// ─── Streamlit Server ───────────────────────────────────────
function startStreamlitServer() {
    const paths = resolvePythonPaths();

    console.log('[NLM] Starting Streamlit server...');
    console.log('[NLM] Project root:', paths.projectRoot);
    console.log('[NLM] Streamlit:', paths.streamlit);
    console.log('[NLM] Web app:', paths.webApp);

    const fs = require('fs');
    if (!fs.existsSync(paths.streamlit)) {
        console.error('[NLM] ERROR: streamlit.exe not found at', paths.streamlit);
        dialog.showErrorBox(
            'Streamlit が見つかりません',
            `以下のパスに streamlit.exe が見つかりません:\n${paths.streamlit}\n\nvenv が正しくセットアップされているか確認してください。`
        );
        app.quit();
        return;
    }

    serverProcess = spawn(paths.streamlit, [
        'run', paths.webApp,
        '--server.port', String(STREAMLIT_PORT),
        '--server.headless', 'true',
        '--server.address', 'localhost',
        '--browser.gatherUsageStats', 'false',
        '--theme.base', 'dark',
    ], {
        cwd: paths.projectRoot,
        env: { ...process.env, PYTHONPATH: path.join(paths.projectRoot, 'src') },
        stdio: ['ignore', 'pipe', 'pipe'],
    });

    serverProcess.stdout.on('data', (data) => {
        console.log('[Streamlit]', data.toString().trim());
    });

    serverProcess.stderr.on('data', (data) => {
        console.error('[Streamlit ERR]', data.toString().trim());
    });

    serverProcess.on('error', (err) => {
        console.error('[NLM] Failed to start Streamlit:', err.message);
        dialog.showErrorBox(
            'サーバー起動エラー',
            `Streamlit の起動に失敗しました:\n${err.message}`
        );
        app.quit();
    });

    serverProcess.on('close', (code) => {
        console.log(`[NLM] Streamlit process exited with code ${code}`);
        // If main window is still alive, it means unexpected crash
        if (mainWindow) {
            dialog.showErrorBox(
                'サーバー停止',
                `Streamlit サーバーが予期せず停止しました (code: ${code}).\nアプリケーションを再起動してください。`
            );
            app.quit();
        }
    });
}

// ─── Wait for server to be ready ────────────────────────────
function waitForServer() {
    return new Promise((resolve, reject) => {
        const startTime = Date.now();

        const poll = () => {
            const elapsed = Date.now() - startTime;
            if (elapsed > SERVER_STARTUP_TIMEOUT_MS) {
                reject(new Error(`Server did not start within ${SERVER_STARTUP_TIMEOUT_MS / 1000}s`));
                return;
            }

            const req = http.get(`http://localhost:${STREAMLIT_PORT}/_stcore/health`, (res) => {
                if (res.statusCode === 200) {
                    resolve();
                } else {
                    setTimeout(poll, POLL_INTERVAL_MS);
                }
            });

            req.on('error', () => {
                setTimeout(poll, POLL_INTERVAL_MS);
            });

            req.setTimeout(2000, () => {
                req.destroy();
                setTimeout(poll, POLL_INTERVAL_MS);
            });
        };

        poll();
    });
}

// ─── Kill server process ────────────────────────────────────
function killServer() {
    if (serverProcess) {
        console.log('[NLM] Stopping Streamlit server...');
        try {
            // On Windows, use taskkill to kill the process tree
            const { execSync } = require('child_process');
            execSync(`taskkill /pid ${serverProcess.pid} /T /F`, { stdio: 'ignore' });
        } catch {
            // Fallback: try SIGTERM
            serverProcess.kill('SIGTERM');
        }
        serverProcess = null;
    }
}

// ─── App Lifecycle ──────────────────────────────────────────
app.whenReady().then(async () => {
    createSplashWindow();
    startStreamlitServer();

    try {
        await waitForServer();
        console.log('[NLM] Streamlit server is ready!');
        createMainWindow();
    } catch (err) {
        console.error('[NLM] Server startup failed:', err.message);
        if (splashWindow) {
            splashWindow.close();
        }
        dialog.showErrorBox(
            'サーバー起動タイムアウト',
            `Streamlit サーバーが ${SERVER_STARTUP_TIMEOUT_MS / 1000} 秒以内に起動しませんでした。\n\n環境を確認してください:\n- Python venv が正しくセットアップされているか\n- streamlit がインストールされているか\n- ポート ${STREAMLIT_PORT} が空いているか`
        );
        killServer();
        app.quit();
    }
});

app.on('window-all-closed', () => {
    killServer();
    app.quit();
});

app.on('before-quit', () => {
    killServer();
});

// Prevent multiple instances
const gotSingleInstanceLock = app.requestSingleInstanceLock();
if (!gotSingleInstanceLock) {
    app.quit();
} else {
    app.on('second-instance', () => {
        if (mainWindow) {
            if (mainWindow.isMinimized()) mainWindow.restore();
            mainWindow.focus();
        }
    });
}
