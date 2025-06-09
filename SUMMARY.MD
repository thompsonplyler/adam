### Project: "It Wasn't Me"

This document outlines the development process, key architectural decisions, and critical lessons learned during the creation of the "It Wasn't Me" game. Its purpose is to serve as a guide for future developers and AI agents, enabling them to understand the project's history and avoid repeating past mistakes.

**Tech Stack**

- **Frontend:** React (with Vite), React Three Fiber/Drei, Mantine UI, React Router
- **Backend:** Flask, SQLAlchemy, Flask-Login, Flask-Cors, Psycopg2
- **Database:** PostgreSQL

**Phase 1: Foundation & Scaffolding**

The project was set up with a standard monorepo structure containing separate `frontend` and `backend` directories. The initial phase focused on scaffolding both applications, including setting up the Python virtual environment, installing Node packages, and establishing basic database models (`User`) and UI components.

**Phase 2: Core Gameplay & API Development**

The core game logic was built out with the following database models: `Game`, `Player`, `Story`, and `Guess`. The backend API was developed incrementally in `backend/app/games.py` to support the full gameplay loop: creating/joining games, submitting stories, starting rounds, guessing, and viewing results.

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

**Current Status**

The application has undergone significant debugging. After chasing several symptoms, we believe we have identified and fixed the final root cause of our authentication failures: a URL mismatch between the frontend API calls (e.g., `/login`) and the backend routes (e.g., `/users/login`). The backend routes have been corrected. We are now pending final user testing to confirm that the entire application flow is stable and works as expected.
