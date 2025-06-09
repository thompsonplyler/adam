from flask import Blueprint, request, jsonify
from flask_login import login_user, logout_user, login_required
from app import db
from app.models import User

main = Blueprint('main', __name__)

@main.route('/')
def index():
    return jsonify({'message': 'Welcome to the Adam game server!'})

@main.route('/users/add', methods=['POST'])
def add_user():
    data = request.get_json()
    if not data or not 'username' in data or not 'password' in data:
        return jsonify({'error': 'Missing username or password'}), 400

    if User.query.filter_by(username=data['username']).first():
        return jsonify({'error': 'Username already exists'}), 400

    user = User(username=data['username'])
    user.set_password(data['password'])
    db.session.add(user)
    db.session.commit()

    return jsonify({'message': 'User created successfully'}), 201

@main.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    user = User.query.filter_by(username=data.get('username')).first()
    if user and user.check_password(data.get('password')):
        login_user(user, remember=True)
        return jsonify({'message': 'Logged in successfully.'})
    return jsonify({'error': 'Invalid username or password'}), 401

@main.route('/logout')
@login_required
def logout():
    logout_user()
    return jsonify({'message': 'Logged out successfully.'}) 