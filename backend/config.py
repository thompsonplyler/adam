import os

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'you-will-never-guess'
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or 'postgresql://postgres:password@localhost:5432/adam'
    SQLALCHEMY_TRACK_MODIFICATIONS = False 
    # Auto-advance timers (seconds)
    GUESS_DURATION_SEC = int(os.environ.get('GUESS_DURATION_SEC', '20'))
    SCOREBOARD_DURATION_SEC = int(os.environ.get('SCOREBOARD_DURATION_SEC', '6'))
    ROUND_INTRO_DURATION_SEC = int(os.environ.get('ROUND_INTRO_DURATION_SEC', '5'))
    # Minimum players (can be made per-mode later)
    MIN_PLAYERS = int(os.environ.get('MIN_PLAYERS', '2'))
    # Final screen hold time (seconds)
    FINAL_SCREEN_DURATION_SEC = int(os.environ.get('FINAL_SCREEN_DURATION_SEC', '20'))
    # Optional: debounce controller actions (ms). 0 disables.
    CONTROLLER_DEBOUNCE_MS = int(os.environ.get('CONTROLLER_DEBOUNCE_MS', '0'))
    # Optional: heartbeat interval for timer worker logs (sec). 0 disables.
    TIMER_HEARTBEAT_SEC = int(os.environ.get('TIMER_HEARTBEAT_SEC', '0'))