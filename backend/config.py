import os

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'you-will-never-guess'
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or 'postgresql://postgres:password@localhost:5432/adam'
    SQLALCHEMY_TRACK_MODIFICATIONS = False 
    # Auto-advance timers (seconds)
    GUESS_DURATION_SEC = int(os.environ.get('GUESS_DURATION_SEC', '20'))
    SCOREBOARD_DURATION_SEC = int(os.environ.get('SCOREBOARD_DURATION_SEC', '6'))
    ROUND_INTRO_DURATION_SEC = int(os.environ.get('ROUND_INTRO_DURATION_SEC', '5'))