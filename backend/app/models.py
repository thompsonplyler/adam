from app import db, login_manager
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
import string
import random

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

class Player(db.Model):
    __tablename__ = 'player'
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), primary_key=True)
    game_id = db.Column(db.Integer, db.ForeignKey('game.id'), primary_key=True)
    score = db.Column(db.Integer, default=0)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    is_creator = db.Column(db.Boolean, default=False, nullable=False)
    user = db.relationship('User', back_populates='games')
    game = db.relationship('Game', back_populates='players')

class User(db.Model, UserMixin):
    __tablename__ = 'user'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), index=True, unique=True, nullable=False)
    password_hash = db.Column(db.String(256))
    games = db.relationship('Player', back_populates='user')
    stories = db.relationship('Story', backref='author', lazy='dynamic')

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def to_dict(self):
        return {
            'id': self.id,
            'username': self.username
        }

    def __repr__(self):
        return f'<User {self.username}>'

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
    game_length = db.Column(db.String(64), default='medium') # short, medium, long
    game_mode = db.Column(db.String(64), default='free_for_all') # free_for_all, teams
    players = db.relationship('Player', back_populates='game')
    stories = db.relationship('Story', foreign_keys='Story.game_id', backref='game', lazy='dynamic')
    current_story_id = db.Column(db.Integer, db.ForeignKey('story.id', name='fk_game_current_story_id', use_alter=True), nullable=True)
    current_story = db.relationship('Story', foreign_keys=[current_story_id], post_update=True)

    def __init__(self, **kwargs):
        super(Game, self).__init__(**kwargs)
        if not self.game_code:
            self.game_code = generate_game_code()

    def to_dict(self, include_players=True):
        data = {
            'id': self.id,
            'game_code': self.game_code,
            'status': self.status,
        }
        if include_players:
            data['players'] = [p.user.username for p in self.players]
        return data

class Story(db.Model):
    __tablename__ = 'story'
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text, nullable=False)
    is_read = db.Column(db.Boolean, default=False)
    results_revealed = db.Column(db.Boolean, default=False, nullable=False)
    game_id = db.Column(db.Integer, db.ForeignKey('game.id'))
    author_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    guesses = db.relationship('Guess', backref='story', lazy='dynamic')

class Guess(db.Model):
    __tablename__ = 'guess'
    id = db.Column(db.Integer, primary_key=True)
    story_id = db.Column(db.Integer, db.ForeignKey('story.id'), nullable=False)
    guesser_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    guessed_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

    # Relationships to get User objects
    guesser = db.relationship('User', foreign_keys=[guesser_id])
    guessed_player = db.relationship('User', foreign_keys=[guessed_id]) 