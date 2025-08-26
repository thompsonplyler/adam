from app import db
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
import json
import string
import random

class User(UserMixin, db.Model):
    __tablename__ = 'user'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(256), nullable=False)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def to_dict(self):
        return {
            'id': self.id,
            'username': self.username,
        }

class Player(db.Model):
    __tablename__ = 'player'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64), nullable=False)
    game_id = db.Column(db.Integer, db.ForeignKey('game.id'), nullable=False)
    score = db.Column(db.Integer, default=0)
    has_submitted_story = db.Column(db.Boolean, default=False, nullable=False)
    game = db.relationship('Game', back_populates='players')
    story = db.relationship('Story', backref='author', uselist=False)

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'game_id': self.game_id,
            'score': self.score,
            'has_submitted_story': self.has_submitted_story
        }

def generate_game_code(length=4):
    """Generate a unique, short game code."""
    while True:
        code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=length))
        if not Game.query.filter_by(game_code=code).first():
            return code

class Game(db.Model):
    __tablename__ = 'game'
    id = db.Column(db.Integer, primary_key=True)
    game_code = db.Column(db.String(4), unique=True, index=True)
    status = db.Column(db.String(64), default='lobby') # lobby, in_progress, finished
    stage = db.Column(db.String(64), nullable=True) # round_intro, scoreboard, finished (when status is finished)
    players = db.relationship('Player', back_populates='game')
    stories = db.relationship('Story', foreign_keys='Story.game_id', backref='game', lazy='dynamic')
    current_story_id = db.Column(db.Integer, db.ForeignKey('story.id', name='fk_game_current_story_id', use_alter=True), nullable=True)
    # Round scaffolding
    current_round = db.Column(db.Integer, nullable=True)
    total_rounds = db.Column(db.Integer, nullable=True)
    play_order = db.Column(db.Text, nullable=True)  # JSON-encoded list of player ids
    
    @property
    def current_story(self):
        if self.current_story_id:
            return Story.query.get(self.current_story_id)
        return None

    def __init__(self, **kwargs):
        super(Game, self).__init__(**kwargs)
        if not self.game_code:
            self.game_code = generate_game_code()

    def to_dict(self):
        players_serialized = []
        for p in self.players:
            pd = p.to_dict()
            if self.current_story_id:
                try:
                    pd['has_guessed_current'] = Guess.query.filter_by(story_id=self.current_story_id, guesser_id=p.id).first() is not None
                except Exception:
                    pd['has_guessed_current'] = False
            players_serialized.append(pd)

        # Build per-round results if story exists
        round_results = []
        if self.current_story_id and self.current_story:
            try:
                author_id = self.current_story.author_id
                for g in Guess.query.filter_by(story_id=self.current_story_id).all():
                    round_results.append({
                        'guesser_id': g.guesser_id,
                        'guessed_player_id': g.guessed_player_id,
                        'correct': (g.guessed_player_id == author_id)
                    })
            except Exception:
                round_results = []

        return {
            'id': self.id,
            'game_code': self.game_code,
            'status': self.status,
            'stage': self.stage,
            'players': players_serialized,
            'current_story': self.current_story.to_dict() if self.current_story else None,
            'current_story_guess_count': Guess.query.filter_by(story_id=self.current_story_id).count() if self.current_story_id else 0,
            'current_round_results': round_results,
            'current_round': self.current_round,
            'total_rounds': self.total_rounds,
            'play_order': json.loads(self.play_order) if self.play_order else None,
        }

class Story(db.Model):
    __tablename__ = 'story'
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text, nullable=False)
    is_read = db.Column(db.Boolean, default=False)
    game_id = db.Column(db.Integer, db.ForeignKey('game.id'), nullable=False)
    author_id = db.Column(db.Integer, db.ForeignKey('player.id'), nullable=False)
    guesses = db.relationship('Guess', backref='story', lazy='dynamic')

    def to_dict(self):
        return {
            'id': self.id,
            'content': self.content,
            'author_id': self.author_id,
        }

class Guess(db.Model):
    __tablename__ = 'guess'
    id = db.Column(db.Integer, primary_key=True)
    story_id = db.Column(db.Integer, db.ForeignKey('story.id'), nullable=False)
    guesser_id = db.Column(db.Integer, db.ForeignKey('player.id'), nullable=False)
    guessed_player_id = db.Column(db.Integer, db.ForeignKey('player.id'), nullable=False)

    guesser = db.relationship('Player', foreign_keys=[guesser_id])
    guessed_player = db.relationship('Player', foreign_keys=[guessed_player_id]) 