from flask import Blueprint, jsonify, request
from app import db, socketio
from app.models import Game, Player, Story, Guess
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

    # Enforce minimum players (configurable later); default 2
    if len(players) < 2:
        return jsonify({'error': 'At least 2 players are required to start'}), 400

    # Compute rounds on start
    game.status = 'in_progress'
    game.stage = 'round_intro'
    import random
    order = [p.id for p in players]
    random.shuffle(order)
    game.play_order = json.dumps(order)
    game.total_rounds = len(order)
    game.current_round = 1
    # Select current story for the first author in play_order
    first_author_id = order[0]
    first_story = Story.query.filter_by(game_id=game.id, author_id=first_author_id).first()
    game.current_story_id = first_story.id if first_story else None
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
        # Enter guessing phase
        game.stage = 'guessing'
        db.session.add(game)
        db.session.commit()
        socketio.emit('state_update', {'game_code': game.game_code}, to=f"game:{game.game_code}", namespace='/ws')
        return jsonify(game.to_dict())

    # guessing -> scoreboard OR scoreboard -> next round/finished
    if game.current_round is None or game.total_rounds is None:
        return jsonify({'error': 'Rounds not initialized'}), 400
    if game.stage == 'guessing':
        # Score this round
        if game.current_story_id:
            story = Story.query.get(game.current_story_id)
            author = Player.query.get(story.author_id) if story else None
            guesses = Guess.query.filter_by(story_id=game.current_story_id).all()
            for g in guesses:
                guesser = Player.query.get(g.guesser_id)
                if not (guesser and author and story):
                    continue
                if g.guessed_player_id == author.id:
                    guesser.score += 1
                    db.session.add(guesser)
                else:
                    author.score += 1
                    db.session.add(author)
            db.session.commit()
        game.stage = 'scoreboard'
        db.session.add(game)
        db.session.commit()
        socketio.emit('state_update', {'game_code': game.game_code}, to=f"game:{game.game_code}", namespace='/ws')
        return jsonify(game.to_dict())
    if game.current_round < game.total_rounds:
        game.current_round += 1
        game.stage = 'round_intro'
        # Update current story to next author per play_order
        try:
            order = json.loads(game.play_order or '[]')
        except Exception:
            order = []
        idx = (game.current_round - 1) if game.current_round else 0
        next_author_id = order[idx] if 0 <= idx < len(order) else None
        next_story = Story.query.filter_by(game_id=game.id, author_id=next_author_id).first() if next_author_id else None
        game.current_story_id = next_story.id if next_story else None
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

@games.route('/<string:game_code>/guess', methods=['POST'])
def submit_guess(game_code):
    data = request.get_json() or {}
    guesser_id = data.get('guesser_id')
    guessed_player_id = data.get('guessed_player_id')

    game = Game.query.filter_by(game_code=game_code.upper()).first_or_404()
    if game.status != 'in_progress' or game.stage != 'guessing':
        return jsonify({'error': 'Not accepting guesses at this time'}), 400
    players = Player.query.filter_by(game_id=game.id).all()
    guesser = Player.query.filter_by(id=guesser_id, game_id=game.id).first()
    guessed = Player.query.filter_by(id=guessed_player_id, game_id=game.id).first()
    if not (guesser and guessed):
        return jsonify({'error': 'Invalid player(s)'}), 400
    # Cannot guess author
    if game.current_story and game.current_story.author_id == guesser.id:
        return jsonify({'error': 'Author cannot guess'}), 400
    # One guess per player per round
    if Guess.query.filter_by(story_id=game.current_story_id, guesser_id=guesser.id).first():
        return jsonify({'error': 'Already guessed this round'}), 400
    new_guess = Guess(story_id=game.current_story_id, guesser_id=guesser.id, guessed_player_id=guessed.id)
    db.session.add(new_guess)
    db.session.commit()
    socketio.emit('state_update', {'game_code': game.game_code}, to=f"game:{game.game_code}", namespace='/ws')
    return jsonify({'message': 'Guess submitted'})
