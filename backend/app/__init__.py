from flask import Flask, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from flask_login import LoginManager
from flask_cors import CORS
from config import Config

db = SQLAlchemy()
bcrypt = Bcrypt()
login_manager = LoginManager()
login_manager.login_view = 'main.login'
login_manager.login_message_category = 'info'

@login_manager.unauthorized_handler
def unauthorized():
    """Redirect unauthorized users to the login page."""
    return jsonify({'error': 'Authentication required. Please log in.'}), 401


def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    db.init_app(app)
    bcrypt.init_app(app)
    login_manager.init_app(app)
    CORS(app, supports_credentials=True, origins=["http://localhost:5173", "http://127.0.0.1:5173"])

    # Import and register blueprints here
    from app.routes import main
    app.register_blueprint(main)

    from app.games import games
    app.register_blueprint(games, url_prefix='/games')

    return app 