from flask import Blueprint, request, jsonify
from .models import db, User, Game, Player
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash

main = Blueprint('main', __name__)

@main.route('/login', methods=['POST', 'OPTIONS'])
def login():
    if request.method == 'OPTIONS':
        return jsonify({'status': 'ok'}), 200
    data = request.get_json()
    user = User.query.filter_by(username=data['username']).first()
    if user and check_password_hash(user.password_hash, data['password']):
        login_user(user)
        return jsonify({"success": True, "user": user.to_dict()})
    return jsonify({"success": False, "message": "Invalid credentials"}), 401

@main.route('/register', methods=['POST', 'OPTIONS'])
def register():
    if request.method == 'OPTIONS':
        return jsonify({'status': 'ok'}), 200
    data = request.get_json()
    if User.query.filter_by(username=data['username']).first():
        return jsonify({"success": False, "message": "Username already exists"}), 400
    
    hashed_password = generate_password_hash(data['password'], method='pbkdf2:sha256')
    new_user = User(username=data['username'], password=hashed_password)
    db.session.add(new_user)
    db.session.commit()
    login_user(new_user)
    return jsonify({"success": True, "user": new_user.to_dict()}), 201

@main.route('/check_login', methods=['GET', 'OPTIONS'])
def check_login():
    if request.method == 'OPTIONS':
        return jsonify({'status': 'ok'}), 200
        
    @login_required
    def protected_check():
        return jsonify({"success": True, "user": current_user.to_dict()})
    
    return protected_check()

@main.route('/logout', methods=['POST', 'OPTIONS'])
@login_required
def logout():
    logout_user()
    return jsonify({"success": True})

@main.route('/games/active')
@login_required
def get_active_games():
    # Find games where the current user is a player
    games = Game.query.join(Player).filter(Player.user_id == current_user.id).all()
    return jsonify([game.to_dict(include_players=False) for game in games]) 