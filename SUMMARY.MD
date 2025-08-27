### Project: "It Wasn't Me"

This document outlines the development process, key architectural decisions, and critical lessons learned during the creation of the "It Wasn't Me" game. Its purpose is to serve as a guide for future developers and AI agents, enabling them to understand the project's history and avoid repeating past mistakes.

**Tech Stack**

- **Frontend:** React (with Vite), Mantine UI, React Router
- **Backend:** Flask, SQLAlchemy, Flask-Login, Flask-Cors, Werkzeug, Psycopg2
- **Database:** PostgreSQL

**Electron Client (New Architecture)**

- Separate Electron app under `electron/` with TypeScript main and Vite + React + Mantine renderer.
- Shared theme lives in `shared/theme.ts` and is imported by both the web frontend and Electron renderer to ensure consistent visuals and easy theme evolution.
- Dev on Windows uses three terminals: `npm run dev:renderer` (Vite at 5174), `npm run dev:main:build` (tsc watch to `dist-main`), and `npm run dev:main` (Electron, waits for 5174).
- Lessons learned:
  - Avoid trying to run `.ts` directly in Electron main. Compile with `tsc` to CommonJS and set `package.json` main to the compiled JS.
  - When coordinating multiple dev processes on Windows PowerShell, prefer separate terminals or use scripts that are PowerShell-friendly (avoid `&&` in user shell; inside npm scripts `&&` is fine).
  - For Socket.IO testing, mirroring handlers on `/` during TESTING unblocks harness limitations; production clients use `/ws`.
  - Vite renderer needs an explicit `root` and `--host` when served from a subdirectory. Without it, Electron can load 404 at `/` even though Vite says it’s “ready”. Setting the renderer’s vite config `root` to the renderer folder and binding `--host` resolved the blank window.
  - Socket.IO and CORS must allow both `http://localhost:5173` (web) and `http://localhost:5174` (Electron renderer) or Electron will show disconnected and the Network tab will show repeated 400s.
  - Do not tie game persistence to the session-owner socket’s instantaneous presence. The Electron renderer can briefly disconnect in dev (HMR), causing accidental teardown and 404 on `/api/games/:code/state`. We now end sessions only on explicit quit, or after a short grace period (~2s) if the session owner does not reconnect.

**Core Gameplay Loop, Timers & State Synchronization (Recent)**

- Backend models: `Game.status` ("lobby" | "in_progress" | "finished") and `Game.stage` ("round_intro" | "guessing" | "scoreboard"; terminal "finished").
- On Start (controller-only), backend sets: `status='in_progress'`, `stage='round_intro'`, `current_round=1`, `total_rounds=players.length`, and `play_order` by join order.
- Advance endpoint (controller-only) transitions: `round_intro → guessing → scoreboard → round_intro(next) → finished`, emitting `state_update` each step.
- Web client shows status badge, stage badge, "Round X of N", and a controller-only Next button wired to `/advance`.
- Auto-advance timers: centralized scheduler runs on every stage change with durations from env (`ROUND_INTRO_DURATION_SEC`, `GUESS_DURATION_SEC`, `SCOREBOARD_DURATION_SEC`), keyed by `(game_id, stage, current_round)`. Guessing also auto-ends early when all non-authors have guessed. Final screen exposes `winners` and holds an optional deadline.

**Organizational Notes**

- Backend routes live in `app/api/` (Blueprints); core game logic moved to `app/services/games/` (`scoring.py`, `scheduler.py`). Routes call services.
- Web client: `GameRoom.jsx` renders via stage-specific components in `src/stages/*`. Finished state short-circuits to a winner-only view for all users.
- Electron renderer mirrors the stage components and displays a read-only view.

**Conventions & Data Shapes**

- `GET /api/games/:code/state` returns:
  - `status`, `stage`, `current_round`, `total_rounds`, `play_order`
  - `current_story`, `current_story_guess_count`
  - `stage_deadline` (unix seconds) for countdowns
  - `round_history` (per-round summary), `winners` on finish
  - `players` with `has_submitted_story`, `has_guessed_current` (derived)

**Recent Fixes & Lessons**

- Second-round timer stalls fixed by centralizing timers and correct task args
- Guessing early-advance on all non-authors guessed (server-scored)
- Controller-only differences limited to lobby Start; final screen unified for all
- Error handling: minimum-players error persists until next click

**Session Owner Lifecycle (Electron is session owner)**

- Electron-created game; web clients only join existing games by code.
- On Electron quit/disconnect: production uses ~2s grace before ending; tests end immediately for determinism. `session_ended` is emitted to room `game:{CODE}` and the backend cleans up related rows (`Player`, `Story`, `Guess`) safely by first clearing `game.current_story_id`.

**Tests**

- All backend tests green. Added validations for: Start initializing rounds/stage; Advance stage pipeline; session_ended emission behavior.
  - Added guessing/scoring flow test; extended pipeline test to reflect guessing stage.

**Phase 5: Core Gameplay Loop & State Synchronization**

- **Centralized Timers & A Nasty Edge Case:**

  - **Problem:** The game intermittently stalled at the second round_intro. Per-path timers and an overly broad de-duplication key prevented scheduling.
  - **Fix:** Introduced a single scheduler that registers timers by `(game_id, stage, current_round)`, invoked after every stage change; removed scattered timers. Also fixed a missing argument bug in the background task call that blocked the second-round intro from firing.

This phase involved implementing the actual gameplay, which uncovered and required fixing several critical bugs related to state management between the server and the clients.

1.  **Author's Waiting Room:**

    - **The Problem:** The player whose story was being guessed saw the same (disabled) guessing interface as everyone else, with no indication of what they were waiting for.
    - **The Fix:** We implemented a dedicated "spectator" view for the story's author. This view now shows the author their own story and two columns: a live list of who has already guessed and who is still thinking. This makes the waiting period interactive.

2.  **Centralizing Game State:**

    - **The Problem:** The game would get "stuck" after the first round. The creator would click "Show Results," but only their screen would change, leaving everyone else in a waiting state indefinitely.
    - **The Root Cause:** This was a major architectural flaw. The decision to show the results was being handled by local state within each client's browser, not by the server.
    - **The Lesson & Solution:** The server must be the single source of truth. We refactored the application to use a new `results_revealed` flag on the `Story` model in the database. A new API endpoint allows the creator to set this flag, and the frontend was completely refactored to derive its view from this server-authoritative state. This ensures all players' screens advance in unison.

3.  **React Infinite Re-render Loop:**

    - **The Problem:** After the first round, the application would crash with a "Too many re-renders" error.
    - **The Root Cause:** In the process of refactoring, a data-fetching function was incorrectly called directly inside the component's main render body. This created an infinite loop: render -> fetch data -> update state -> trigger re-render.
    - **The Fix:** The data fetching logic was moved into a `useEffect` hook. This is the correct React pattern, ensuring the data is only fetched when its specific dependencies (like the story ID) change, not on every single render.

4.  **Database Seeding & Password Hashing:**
    - **The Problem:** After a database reset, logins would fail with an `Invalid hash method` error.
    - **The Root Cause:** The database seeding script was using the `flask_bcrypt` library to hash passwords, but the login verification function was using the `werkzeug.security` library. The two libraries use incompatible hash formats.
    - **The Fix:** The seeding script was corrected to use the `user.set_password()` method, ensuring that the same `werkzeug` library is used for both creating and checking passwords.

**Phase 4: Polish & Infrastructure**

With the user session and game lobby systems stabilized, the focus shifted to improving the user experience for joining/leaving games and enhancing developer tooling.

1.  **Graceful Handling of Non-Existent Games:**

    - **The Problem:** Accessing a URL for a game that had been deleted or never existed (`/game/<invalid_code>`) caused the frontend to crash. The `GameRoom.jsx` component was polling a state endpoint, receiving a `404 Not Found` response (as plain HTML), and failing on an unhandled JSON parsing error.
    - **The Fix:** This was a two-part solution. First, the generic `request` function in `frontend/src/api.js` was refactored to be more robust. It now checks the response's `Content-Type` and status code, attaching the status to the thrown error object. This allows calling components to differentiate between error types. Second, the `GameRoom.jsx` component was updated to specifically catch errors where `err.status === 404`. Upon catching this specific error, it stops polling, displays a user-friendly "Game Not Found" message, and automatically redirects the user back to the lobby after a few seconds.

2.  **Database Reset & Seeding Utility:**
    - **The Goal:** Create a simple command to wipe and re-seed the database with test users for consistent development and testing.
    - **The Implementation:** A custom Flask CLI command, `flask db-reset`, was created in `backend/app/__init__.py`. This command drops all tables, recreates them from the models, and seeds three test users.
    - **The Pain Point - Circular Dependencies:** The initial implementation failed with a `sqlalchemy.exc.CircularDependencyError`. The `Game` model depended on the `Story` model (via `current_story_id`), and `Story` depended on `Game` (via `game_id`). SQLAlchemy didn't know which table to drop first.
    - **The Lesson & Solution:** After several failed attempts to resolve this within SQLAlchemy, the definitive solution was to step outside the ORM. We used the `psql` command-line tool to manually run `DROP SCHEMA public CASCADE; CREATE SCHEMA public;`. This completely wiped the database, allowing the `flask db-reset` command to run successfully on a clean slate. This serves as a crucial reminder: when ORM-level schema tools fail due to inconsistent state, sometimes the most effective solution is to perform a hard reset directly on the database.

**Phase 1: Foundation & Scaffolding**

The project was set up with a standard monorepo structure containing separate `frontend` and `backend` directories. The initial phase focused on scaffolding both applications, including setting up the Python virtual environment, installing Node packages, and establishing basic database models (`User`) and UI components.

**Phase 2: Initial Model & API Scaffolding**

The database models to support the eventual gameplay (`Game`, `Player`, `Story`, `Guess`) were created. The initial backend API endpoints were scaffolded in `backend/app/games.py` to provide the _structure_ for a full gameplay loop (creating/joining, submitting, guessing, etc.). However, the frontend implementation and testing of the core gameplay itself remains to be done. The work so far has focused entirely on the user authentication and lobby management systems.

**Phase 3: Critical Lessons & Debugging Chronicles**

The connection between the frontend and backend exposed a series of significant challenges. Overcoming these was crucial to the project's success.

1.  **CORS & Authentication Hell:** This was the single largest pain point.

    - **Initial Problem:** `CORS Missing Allow Origin`. This was solved by installing `Flask-Cors` and configuring it to support credentials from the frontend's origin. The frontend `api.js` was also updated to include `credentials: 'include'` in all `fetch` requests.
    - **The Root Cause:** After the initial fix, we were plagued by persistent `404 Not Found` errors on `OPTIONS` preflight requests, which manifested as `CORS Preflight Did Not Succeed` errors in the browser. We mistakenly chased symptoms by modifying `@login_required` decorators. **The true, underlying issue was a simple URL mismatch.** The frontend was calling `/login`, while the backend routes were incorrectly defined with a `/users/` prefix (e.g., `/users/login`).
    - **The Lesson:** Always triple-check that frontend API calls and backend route definitions match _exactly_. A `404 Not Found` on a preflight request is a strong indicator of a URL mismatch, not necessarily a complex CORS policy issue. We also learned that `Flask-Login`'s default configuration (`login_manager.login_view`) is not suitable for a JSON API and should be removed.

2.  **Database Integrity Violation:** When the last player left a game, the server would crash with a `ForeignKeyViolation`.

    - **The Problem:** The cleanup logic tried to delete all `Story` records associated with the game _before_ breaking the link from the `Game` table's `current_story_id` column.
    - **The Fix:** Before deleting the stories, we added a step to set `game.current_story_id = None` and commit the change, severing the foreign key link and allowing the cleanup to proceed.

3.  **Frontend State Management:** We encountered several bugs where the UI would not display the user's name or would handle game logic incorrectly.

    - **The Problem:** The `onLogin` and `checkLogin` functions were storing the entire server response object (e.g., `{ success: true, user: {...} }`) in the React state, instead of just the nested `user` object.
    - **The Fix:** We corrected the `handleLogin` and `verifyUser` functions in `App.jsx` to properly extract `response.user` before setting the state. This ensured the rest of the application had access to a clean and predictable user object.

4.  **Full-Page Reloads on Navigation:** Leaving a game would cause a full-page reload and log the user out.

    - **The Problem:** We were using `window.location.href = '/'` for navigation.
    - **The Fix:** This was replaced with the `useNavigate` hook from `react-router-dom` (`navigate('/')`), which correctly handles internal navigation in a Single-Page Application without losing state.

5.  **Incomplete Model Serialization:** API endpoints would crash when trying to return database objects as JSON.
    - **The Problem:** The `User` and `Game` models were missing `.to_dict()` methods, causing an `AttributeError` whenever an endpoint tried to serialize them for a response. The most recent occurrence of this caused a `500 Internal Server Error` on the `/games/active` endpoint, which prevented the lobby from loading.
    - **The Fix:** We added `to_dict()` methods to both the `User` and `Game` models, ensuring they could be reliably converted to JSON.
