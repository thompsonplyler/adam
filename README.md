# It Wasn't Me – Developer Setup

This repo contains a Flask backend, a React (Vite + Mantine) web client, and a TypeScript Electron display client. The backend is the single source of truth; Electron starts/ends sessions; web clients join with a 4‑letter code.

## Prerequisites

- Python 3.10+
- Node.js 18+
- PostgreSQL (local for dev)
- A `.env` with at least `DATABASE_URL` and `SECRET_KEY` (do not commit). The backend reads these values.

## Backend (Flask)

1. Create and activate a virtual environment.
2. Install dependencies:
   ```bash
   pip install -r backend/requirements.txt
   ```
3. Ensure PostgreSQL is running and `DATABASE_URL` points to a database you can access.
4. Initialize or reset the database (PowerShell):
   ```powershell
   cd backend; venv\Scripts\activate; flask db-reset
   ```
5. Run the dev server with timers/env (PowerShell-friendly):
   ```powershell
   cd backend; venv\Scripts\activate;
   $env:FLASK_APP="run.py"; $env:FLASK_ENV="development";
   $env:ROUND_INTRO_DURATION_SEC="5"; $env:GUESS_DURATION_SEC="20"; $env:SCOREBOARD_DURATION_SEC="6";
   $env:MIN_PLAYERS="2"; $env:FINAL_SCREEN_DURATION_SEC="20";
   flask run
   ```
   - API base URL: `http://localhost:5000/api`
   - Websocket namespace: `http://localhost:5000/ws`

### Routing organization (Flask Blueprints)

- The backend API is organized using Blueprints under `app/api/`.
- Current modules:
  - `app/api/games.py` → mounted at `/api/games`
- This structure makes it easy to add versioning later (e.g. `app/api/v1/...`) and keeps domains separated (auth, games, admin, etc.).
- A legacy `app/games.py` file remains as a stub for now and can be removed once all imports are updated.

### Database verification (PowerShell)

To confirm the backend can reach your configured database, you can run:

```powershell
cd backend; venv\Scripts\activate; python -c "from app import create_app, db; a=create_app(); ctx=a.app_context(); ctx.push(); print('DB URL:', db.engine.url); c=db.engine.connect(); c.close(); print('DB CONNECTED')"
```

### Manual real-time verification (must-pass)

1. Start backend and frontend as above.
2. Start Electron (see below), click "Start Game" to create a code.
3. In the web app, enter the code on the home screen to join from each player.
4. Each player submits a story; controller (first to join) sees "Start Game" when all are ready. Starting the game flips everyone to "In Progress".
5. During play: server auto-advances stages; guessing ends early if all non-authors guessed; scoreboard shows totals; final screen shows winner(s) only.

## Frontend (React + Vite)

1. Install deps:
   ```bash
   cd frontend
   npm install
   ```
2. Create `frontend/.env` if needed to point to a remote backend:
   ```
   VITE_API_URL=http://localhost:5000
   ```
3. Run dev server:
   ```powershell
   npm run dev
   ```
4. Open the app at the URL shown by Vite (usually `http://localhost:5173`).

### Quick Flow

- Electron: click "Start Game" to create a lobby and code.
- Players join at `/game/CODE`, enter a name, submit a story.
- Controller (first joiner) starts the game once all have submitted.
- Stages: round_intro → guessing → scoreboard → next round … → finished. Timers are server-driven.

## Electron app (TypeScript)

Separate Electron client with shared Mantine theme. Electron is the session owner (lifecycle) but not a gameplay user.

Dev (Windows):

1. Terminal A:
   ```powershell
   cd electron; npm install; npm run dev:renderer
   ```
2. Terminal B:
   ```powershell
   cd electron; npm run dev:main:build
   ```
3. Terminal C:
   ```powershell
   cd electron; npm run dev:main
   ```
   You should see an Electron window that loads `http://localhost:5174`.

Usage (local):

- Start Game (creates lobby + code)
- Share the code; web clients join at `/game/CODE`
- When all players are ready, controller clicks Start Game
- Quit Lobby in Electron ends the session (graceful cleanup) and boots web clients to the join screen

Troubleshooting (Windows):

- If Electron window is blank/404, ensure `electron/renderer/vite.config.ts` sets `root` to the renderer directory and server `{ host: true, port: 5174 }`, and that you started `npm run dev:renderer` from `electron/`.
- If Socket.IO shows repeated 400s in devtools, confirm backend CORS and Socket.IO allowed origins include `http://localhost:5174` (adjusted in `backend/app/__init__.py`).

Current capabilities

- Start a game from the Electron window (creates a lobby and displays a copyable code)
- Players join from the web client at `/game/CODE`
- Electron shows connection status and live player list updates via Socket.IO `state_update`

### Stage auto-advance timers (backend-driven)

The backend auto-advances the game at each stage based on environment-configurable durations. Set these in your PowerShell session before `flask run`:

```powershell
venv\Scripts\activate; $env:ROUND_INTRO_DURATION_SEC="5"; $env:GUESS_DURATION_SEC="20"; $env:SCOREBOARD_DURATION_SEC="6"; flask run
```

Clients display stage countdowns. Final screen does not auto-redirect; players choose next action.

Config toggles (optional):

- `CONTROLLER_DEBOUNCE_MS` – debounces controller actions (start/advance). Default 0.
- `TIMER_HEARTBEAT_SEC` – logs timer heartbeats. Default 0.

## Deployment (Backend)

- Recommended: Gunicorn + eventlet for Flask-SocketIO
  ```bash
  gunicorn --worker-class eventlet -w 1 run:app --bind 0.0.0.0:5000
  ```
- Required env: `DATABASE_URL`, `SECRET_KEY`, plus stage durations and `MIN_PLAYERS` as needed
- Ensure your platform enables websockets and long-polling

## Tests

- Backend: pytest covers HTTP flows, socket basics, and session owner lifecycle.
- Frontend: smoke tests planned for `GameRoom` and socket behavior.

Refer to `GAME-PLAN.MD` for test gates that must pass before feature development proceeds.
