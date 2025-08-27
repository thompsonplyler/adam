# Game Development Plan

This document outlines the phased development plan to evolve the "It Wasn't Me" game from its current state to the full vision described by Adam. The core principle is to build foundational features first and then layer more complex logic and polish on top.

## Must-Pass Test Gates (No Forward Progress Without Green)

These checks must pass before moving to the next step. If any gate fails later, we stop and fix before adding features.

- API base path alignment: Frontend calls `/api/...` and backend serves under `/api/...` with CORS enabled.
- Backend routing best practice: Blueprints under `app/api` are the organizing principle for API modules (e.g., `games`, `auth`).
- HTTP smoke tests: create game, join game, get state, submit story all succeed (pytest).
- Websocket basic connectivity: client can connect to `/ws`, join `game:{CODE}` room, receive `state_update` when a story is submitted (pytest-socketio where applicable and manual check via React client).
- Idempotent page route: `/game/:code` loads and refreshes without 404s.
- Documentation: README instructions allow a clean setup by a new developer to run backend, frontend, and Electron test client against localhost.

Current status:

- DB connectivity verified against configured PostgreSQL instance.
- HTTP endpoints verified by tests.
- Socket tests pass using test-only mirror; browser/Electron manual checks next.
- Electron main compiles from TypeScript (tsc → dist-main) and loads renderer (Vite at 5174) on Windows.
- Game stage pipeline implemented and tested: `status` (lobby → in_progress → finished) with per-round `stage` (round_intro → guessing → scoreboard, then finished).
- Centralized stage timers implemented (intro/guessing/scoreboard) using a scheduler keyed by `(game_id, stage, current_round)`; env-configurable durations; visible countdowns on web/Electron.

### Host-Owned Session Model (Authoritative Electron)

- Electron is the host and single source of truth for an active game session.
- Only Electron can create a game and generate a join code. Web clients never create games.
- If Electron disconnects (host stops), the session is terminated and all web clients must be booted with a clear "Session ended" state.
- The first web client to join a lobby becomes the controller and can start the game once all players have readied.

Must-pass gates for this model:

- Host heartbeat/room presence is detected; if absent beyond a short grace period, session is ended and DB is cleaned.
- Web clients joining a non-existent or ended session receive a clear error and return to the code entry screen.
- Web default landing is "Enter code"; Electron default is "Start Game".

---

## Phase 1: Game Settings (The Foundation)

**Goal:** Allow the game host to configure the game before it starts. This is the prerequisite for all other gameplay variations.

1.  **Backend - Database:**
    - Add `game_mode` (e.g., 'free_for_all', 'teams') and `game_length` (e.g., 'short', 'medium', 'long') fields to the `Game` model in `backend/app/models.py`.
2.  **Frontend - UI:**
    - Create a new "Create Game" screen that appears before the lobby.
    - This screen will contain UI elements (like radio buttons or a select dropdown) for the host to choose the Game Mode and Game Length.
3.  **Backend - API:**
    - Update the `/games/create` endpoint to accept the `game_mode` and `game_length` parameters.
    - Save these values to the new columns in the `Game` table when a new game is created.

---

## Phase 2: Implementing Teams

**Goal:** Introduce the concept of teams, allowing players to join a team and altering the core guessing rules.

1.  **Backend - Database:**
    - Add a `team` (e.g., 'team1', 'team2') field to the `Player` model.
2.  **Frontend - UI:**
    - Update the Lobby view. If the game mode is "Teams," display UI for players to select a team.
    - Visually group players by their chosen team in the player list.
3.  **Backend - Logic:**
    - Modify the guessing logic in `backend/app/games.py`.
    - When a guess is submitted, if the game mode is "Teams," validate that the guessed player is not on the same team as the guesser.

---

## Phase 3: Overhauling the Gameplay Loop

**Goal:** Adapt the existing gameplay loop to accommodate a fixed number of rounds and new scoring rules.

1.  **Backend - Database & Logic:**
    - Add a `current_round` integer field to the `Game` model.
    - Implement logic to increment this counter each time a new story is presented.
2.  **Backend - Scoring Logic:**
    - Update the scoring endpoint in `games.py`.
    - Before calculating points, check if `current_round` is within the last two rounds of the `game_length`. If so, double all points awarded for that round.
3.  **Backend/Frontend - Game End Condition:**
    - Change the logic that ends the game. Instead of ending when stories run out, the game should end when `current_round` exceeds the total number of rounds defined by `game_length`.
    - When the game ends, the `game.status` should be set to 'finished', and the UI should transition all players to a new "Winner" screen.

---

## Phase 4: The Final Experience

**Goal:** Create a satisfying conclusion and the ability to play again.

1.  **Frontend - UI:**
    - Design and build a new React component for the "Winner Announcement" screen. This screen will display the winning player or team and the final scores.
2.  **Frontend/Backend - Replay Functionality:**
    - Add "Play Again" and "Return to Main Menu" buttons to the winner screen.
    - "Play Again" should ideally create a new game with the same settings and players.
    - "Return to Main Menu" should navigate the user back to the initial landing/login page.

---

## Future Polish (Post-Core Implementation)

These items from Adam's vision can be implemented after the core gameplay is robustly in place:

- Quick Open Screen animation
- Descriptive Verbiage / how-to-play animations
- Story Prompt Themes
- AI-assisted spell-checking and word replacement
- Player icon selection
- Superlative awards (e.g., "Most Deceptive")
- Suspenseful animations for revealing the storyteller.

---

## Active Tasks Log (Architecture & Connectivity)

- Standardize API under `/api` and align frontend calls. [Implemented]
- Introduce Flask-SocketIO server with `/ws` namespace and per-game rooms `game:{CODE}`. [Implemented]
- Emit `state_update` on story submission to the appropriate room. [Implemented]
- Frontend Socket.IO client joins room and refreshes state on `state_update`. [Implemented]
- Reorganize backend routes using Blueprints under `app/api/` and document as routing principle. [Implemented]
- Add minimal Electron client for connectivity tests (connect, join room, log events). [Planned]
- Add backend pytest for HTTP endpoints and a socket echo/room test. [Planned]

Updated/added (this iteration):

- Backend rounds and stages implemented: `total_rounds`, `current_round`, `play_order` initialized on Start; `/advance` endpoint cycles `round_intro ↔ scoreboard` per round and finalizes with `finished`. [Implemented]
- Controller-only Start and Next flows validated in UI. [Implemented]
- Session owner disconnect: production keeps ~2s grace; tests end immediately for determinism. [Implemented]
- Auto-advance timers for stages with centralized scheduler; countdowns shown in clients. [Implemented]

TODOs:

- Replace test-only socket namespace mirror by making the test harness reliably connect to `/ws` so production and tests share identical namespaces.

Each item above must be covered by tests and/or manual verification steps listed in README.

---

## Near-term Roadmap (Electron small steps)

1. Electron renderer MVP

- Code entry screen to join game by code
- Connection status badge; room indicator
- Players list (GET `/api/games/:code/state`) with submission status
- Live refresh on `state_update` from `/ws`
- Controller-only "Start Game" once all ready [Implemented]
- Stage badges, round counter, and controller-only Next [Implemented]
- Visible countdown timers per stage [Implemented]

### Near-term tasks

- Refactor web/Electron to stage-specific components loaded from global state (Zustand), fully unmount previous stage views.
- Persist per-round results list; show a final recap screen at Finished.
- Add backend logging toggle and heartbeat guard to detect/tolerate stalls (optional).
- Expand tests to cover timer-driven auto-advance with mocked durations.

2. Developer experience

- Document three-terminal dev flow on Windows (renderer, tsc watch, electron)
- Add basic CSP for renderer in dev to quiet warnings

3. Tests & gates

- Unit tests for socket client and simple rendering
- Keep backend tests green; no change to HTTP/socket contracts

### Incremental Changes (next iteration)

- Backend: introduce host lifecycle signals (heartbeat or presence-based) and a `session_ended` event; delete/cleanup game on host end. [Partially Implemented]
- Frontend (web): make the default screen an "Enter code" join view; designate first joiner as controller; add readiness gating. [Implemented]
- Electron: ensure UI never exposes "Join"; keep only "Start Game" and lobby/display. [In Progress]

---

## Spec Alignment – Remaining Work from Design Spec (non-yellow)

This section tracks items from the original design spec that remain to be implemented in v1 (yellow items are explicitly deferred).

1. Game Modes

- Free‑for‑All (current behavior) [Implemented]
- Teams (new)
  - Add `team` field to `Player`
  - Lobby UI to pick team (Electron display and web client)
  - Guessing restrictions: show only opposite‑team names as options
  - Scoring: keep current rules per round; totals per player (future: team totals)
  - Tests: team assignment, guessing filter, scoring unchanged

2. Game Length / Stories‑per‑Player

- Host selects game length at session creation (Electron): Short/Average/Marathon → maps to stories per player (e.g., 1/2/3)
- Backend adds `stories_per_player` (or `rounds_per_player`) to `Game`
- Lobby requires each player to submit all of their stories upfront
- Compute `total_rounds = players_count * stories_per_player`
- Play order: expand authors list so each player appears `stories_per_player` times, then shuffle
- Validations: cannot start until each player submitted exactly `stories_per_player` stories
- Tests: total rounds calculation, start validation, multi‑story rotation

3. Reveal Author callout on Scoreboard

- Explicitly show: “Author: <name>” on scoreboard [Planned]

4. Final Screen polish

- Winner(s) shown (done). Add “Play Another” → creates new Electron session and shows new code to all clients [Planned]

5. Must‑Pass Gates for the above

- Teams: team choice persists; guessing only shows opposite team; tests green
- Game length: cannot start early; `total_rounds` correct; rotation covers each story once
- No regressions: timers, early guessing end, scoring, session lifecycle, and winner screen remain correct

---

## Implementation Plan (next milestones)

1. Data model & API

- Add `Game.game_mode` ('free_for_all' | 'teams'), `Game.stories_per_player` (int)
- Add `Player.team` (nullable early; required when teams mode)
- Update serializers and state to expose these fields

2. Host (Electron)

- Pre‑lobby configuration screen: select mode + length
- Broadcast chosen settings to web clients with first `state_update`

3. Web (lobby)

- If teams mode, allow team selection
- Story submission UI supports multiple stories up‑front with clear progress/counter
- Start button enabled only when all players hit the required count

4. Engine

- Build multi‑story play order and set `total_rounds`
- Enforce guesser filtering in teams mode

5. Tests

- Unit/integration for start validation, play order, teams guessing filter, and scoreboard author callout
