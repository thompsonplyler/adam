from flask import Blueprint, jsonify, request
from app import db, socketio
from app.models import Game, Player, Story
import json


games = Blueprint('games', __name__)


@games.route('/create', methods=['POST'])
def create_game_unauthed():
    new_game = Game()
    db.session.add(new_game)
    db.session.commit()
    return jsonify({
        'message': 'New game created!',
        'game_code': new_game.game_code
    }), 201


@games.route('/join', methods=['POST'])
def join_game_unauthed():
    data = request.get_json()
    game_code = data.get('game_code')
    name = data.get('name')
    if not all([game_code, name]):
        return jsonify({'error': 'Game code and player name are required'}), 400

    game = Game.query.filter_by(game_code=game_code.upper()).first()
    if not game:
        return jsonify({'error': 'Game not found'}), 404

    if game.status != 'lobby':
        return jsonify({'error': 'This game is not in the lobby'}), 403

    new_player = Player(name=name, game_id=game.id)
    db.session.add(new_player)
    db.session.commit()

    return jsonify(new_player.to_dict()), 201


@games.route('/<string:game_code>/stories', methods=['POST'])
def submit_story(game_code):
    data = request.get_json()
    player_id = data.get('player_id')
    story_content = data.get('story')

    if not all([player_id, story_content]):
        return jsonify({'error': 'Player ID and story content are required'}), 400

    game = Game.query.filter_by(game_code=game_code.upper()).first_or_404()
    player = Player.query.filter_by(id=player_id, game_id=game.id).first_or_404()

    if game.status != 'lobby':
        return jsonify({'error': 'You can only submit stories while the game is in the lobby.'}), 400

    existing_story = Story.query.filter_by(author_id=player.id, game_id=game.id).first()
    if existing_story:
        return jsonify({'error': 'You have already submitted a story for this game.'}), 400

    new_story = Story(
        content=story_content,
        author_id=player.id,
        game_id=game.id
    )
    db.session.add(new_story)

    player.has_submitted_story = True
    db.session.add(player)

    db.session.commit()

    # Emit live update to all clients in the game room
    socketio.emit('state_update', {'game_code': game.game_code}, to=f"game:{game.game_code}", namespace='/ws')

    return jsonify({'message': 'Story submitted successfully'}), 201


@games.route('/<string:game_code>/state', methods=['GET'])
def get_game_state(game_code):
    game = Game.query.filter_by(game_code=game_code.upper()).first_or_404()
    return jsonify(game.to_dict())


@games.route('/<string:game_code>/start', methods=['POST'])
def start_game(game_code):
    data = request.get_json() or {}
    controller_id = data.get('controller_id')

    game = Game.query.filter_by(game_code=game_code.upper()).first_or_404()
    if game.status == 'in_progress':
        # Idempotent start: already started
        return jsonify(game.to_dict())
    if game.status != 'lobby':
        return jsonify({'error': 'Game is not in lobby'}), 400

    players = Player.query.filter_by(game_id=game.id).all()
    if not players:
        return jsonify({'error': 'No players in game'}), 400

    expected_controller = min(p.id for p in players)
    if controller_id != expected_controller:
        return jsonify({'error': 'Only the first player to join may start the game'}), 403

    if any(not p.has_submitted_story for p in players):
        return jsonify({'error': 'All players must submit a story before starting'}), 400

    # Compute rounds on start
    game.status = 'in_progress'
    game.stage = 'round_intro'
    order = sorted([p.id for p in players])
    game.play_order = json.dumps(order)
    game.total_rounds = len(order)
    game.current_round = 1
    db.session.add(game)
    db.session.commit()

    socketio.emit('state_update', {'game_code': game.game_code}, to=f"game:{game.game_code}", namespace='/ws')
    return jsonify(game.to_dict())


@games.route('/<string:game_code>/advance', methods=['POST'])
def advance_round(game_code):
    data = request.get_json() or {}
    controller_id = data.get('controller_id')

    game = Game.query.filter_by(game_code=game_code.upper()).first_or_404()
    if game.status == 'finished':
        return jsonify(game.to_dict())
    if game.status != 'in_progress':
        return jsonify({'error': 'Game is not in progress'}), 400

    players = Player.query.filter_by(game_id=game.id).all()
    if not players:
        return jsonify({'error': 'No players in game'}), 400
    expected_controller = min(p.id for p in players)
    if controller_id != expected_controller:
        return jsonify({'error': 'Only the controller may advance'}), 403

    # Stage pipeline
    if game.stage == 'round_intro':
        game.stage = 'scoreboard'
        db.session.add(game)
        db.session.commit()
        socketio.emit('state_update', {'game_code': game.game_code}, to=f"game:{game.game_code}", namespace='/ws')
        return jsonify(game.to_dict())

    # scoreboard -> next round or finished
    if game.current_round is None or game.total_rounds is None:
        return jsonify({'error': 'Rounds not initialized'}), 400
    if game.current_round < game.total_rounds:
        game.current_round += 1
        game.stage = 'round_intro'
        db.session.add(game)
        db.session.commit()
        socketio.emit('state_update', {'game_code': game.game_code}, to=f"game:{game.game_code}", namespace='/ws')
        return jsonify(game.to_dict())

    game.status = 'finished'
    game.stage = 'finished'
    db.session.add(game)
    db.session.commit()
    socketio.emit('state_update', {'game_code': game.game_code}, to=f"game:{game.game_code}", namespace='/ws')
    return jsonify(game.to_dict())
