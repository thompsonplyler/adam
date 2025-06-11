# Game Development Plan

This document outlines the phased development plan to evolve the "It Wasn't Me" game from its current state to the full vision described by Adam. The core principle is to build foundational features first and then layer more complex logic and polish on top.

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
