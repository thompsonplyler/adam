from flask import Blueprint, jsonify, request
from app import db, socketio
from app.models import Game, Player, Story


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

    # Check if all players have submitted their stories to start the game
    total_players = Player.query.filter_by(game_id=game.id).count()
    if total_players < 2:
        return jsonify({'message': 'Story submitted. Waiting for more players.'}), 201

    submitted_stories = Story.query.filter_by(game_id=game.id).count()

    if total_players == submitted_stories:
        game.status = 'in_progress'
        db.session.commit()

    # Emit live update to all clients in the game room
    socketio.emit('state_update', {'game_code': game.game_code}, to=f"game:{game.game_code}", namespace='/ws')

    return jsonify({'message': 'Story submitted successfully'}), 201


@games.route('/<string:game_code>/state', methods=['GET'])
def get_game_state(game_code):
    game = Game.query.filter_by(game_code=game_code.upper()).first_or_404()
    return jsonify(game.to_dict())


