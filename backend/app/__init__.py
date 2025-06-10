from flask import Flask, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from flask_login import LoginManager
from flask_cors import CORS
from flask_migrate import Migrate
from config import Config

db = SQLAlchemy()
bcrypt = Bcrypt()
login_manager = LoginManager()
migrate = Migrate()

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    db.init_app(app)
    bcrypt.init_app(app)
    login_manager.init_app(app)
    migrate.init_app(app, db)
    CORS(app, supports_credentials=True, origins=["http://localhost:5173", "http://127.0.0.1:5173"])

    # Import and register blueprints here
    from app.main import main
    app.register_blueprint(main)

    from app.games import games
    app.register_blueprint(games, url_prefix='/games')

    @app.cli.command('db-reset')
    def db_reset_command():
        """Drops, recreates, and seeds the database."""
        from app.models import User
        with app.app_context():
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

    return app 