from flask import Flask, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from flask_login import LoginManager
from flask_cors import CORS
from flask_migrate import Migrate
from flask_socketio import SocketIO
import importlib
import click
from config import Config

db = SQLAlchemy()
bcrypt = Bcrypt()
login_manager = LoginManager()
migrate = Migrate()
allowed_origins = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:5174",
    "http://127.0.0.1:5174",
]
socketio = SocketIO(cors_allowed_origins=allowed_origins, async_mode=None)

def create_app(config_class=Config):
    flask_app = Flask(__name__)
    flask_app.config.from_object(config_class)

    db.init_app(flask_app)
    bcrypt.init_app(flask_app)
    login_manager.init_app(flask_app)
    migrate.init_app(flask_app, db)
    CORS(flask_app, supports_credentials=True, origins=allowed_origins)

    # Initialize Socket.IO after app is created
    socketio.init_app(flask_app, cors_allowed_origins=allowed_origins)

    # Import and register blueprints here
    from app.main import main
    flask_app.register_blueprint(main)

    from app.api.games import games
    # Mount game routes under /api to match frontend API client
    flask_app.register_blueprint(games, url_prefix='/api/games')

    # Register Socket.IO event handlers
    # Importing here ensures the handlers bind to the initialized socketio instance
    # Use importlib to avoid shadowing the local Flask app variable name
    try:
        from app.socketio_events import register_socketio_handlers
        register_socketio_handlers(testing=flask_app.config.get('TESTING', False))
    except Exception as exc:
        # Avoid crashing app init if events module has yet to be created during early setup
        flask_app.logger.warning(f"SocketIO events not loaded: {exc}")

    # Flask-Login user loader
    from app.models import User

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    @click.command('db-reset')
    def db_reset_command():
        """Drops, recreates, and seeds the database."""
        from app.models import User
        with flask_app.app_context():
            db.drop_all()
            db.create_all()

            # Seed users
            users = ['testuser1', 'testuser2', 'testuser3']
            for u in users:
                user = User(username=u)
                user.set_password('password')
                db.session.add(user)
            
            db.session.commit()
            print('Database has been reset and seeded!')

    flask_app.cli.add_command(db_reset_command)

    return flask_app