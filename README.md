# It Wasn't Me – Developer Setup

This repo contains a Flask backend and a React (Vite + Mantine) frontend. A minimal Electron client is provided to validate websocket connectivity and room-based updates. The backend is designed to be deployed to Render with PostgreSQL.

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
4. Initialize the database:
   ```bash
   # Optional utility to reset and seed users
   cd backend
   python -m flask --app run db-reset
   ```
5. Activate the virtual environment and run the dev server via Flask (PowerShell syntax shown):
   ```powershell
   cd backend; venv\Scripts\activate; $env:FLASK_APP="run.py"; $env:FLASK_ENV="development"; flask run
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

### Manual real-time verification

1. Start backend and frontend as above.
2. In the web app, click Create Game and copy the game code.
3. Open two browser tabs to `/game/CODE`, join with two different names.
4. Submit a story in one tab. The other tab should update nearly instantly (socket `state_update`).

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

- From the Home page, click "Create Game" to get a `GAME_CODE`.
- Share the URL `/game/GAME_CODE` with players.
- Players join with a display name and submit a story.
- When anyone submits a story, connected clients in that game room receive a `state_update` over websockets and refresh the game state.

## Electron app (TypeScript)

Separate Electron client with shared Mantine theme.

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

Troubleshooting (Windows):

- If Electron window is blank/404, ensure `electron/renderer/vite.config.ts` sets `root` to the renderer directory and server `{ host: true, port: 5174 }`, and that you started `npm run dev:renderer` from `electron/`.
- If Socket.IO shows repeated 400s in devtools, confirm backend CORS and Socket.IO allowed origins include `http://localhost:5174` (adjusted in `backend/app/__init__.py`).

Current capabilities

- Start a game from the Electron window (creates a lobby and displays a copyable code)
- Players join from the web client at `/game/CODE`
- Electron shows connection status and live player list updates via Socket.IO `state_update`

## Render Deployment (Backend)

- Set environment variables: `DATABASE_URL`, `SECRET_KEY`.
- Build command: `pip install -r backend/requirements.txt`
- Start command: `python backend/run.py`
- Make sure Render service enables websockets.

## Tests

- Backend: pytest planned for HTTP endpoints and basic socket events.
- Frontend: tests planned for `GameRoom` and socket client behavior.

Refer to `GAME-PLAN.MD` for test gates that must pass before feature development proceeds.
