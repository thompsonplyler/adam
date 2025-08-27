from flask import Blueprint, jsonify, request, current_app
from app import db, socketio
from app.models import Game, Player, Story, Guess
import json
from typing import Set, Tuple
from app.services.games.scoring import score_current_round as svc_score_current_round
from app.services.games.scheduler import schedule_stage_timer as svc_schedule_stage_timer


games = Blueprint('games', __name__)

# Centralized stage timer scheduler (runtime-only; disabled in tests)
_scheduled_stage_keys: Set[Tuple[int, str, int]] = set()

def _score_current_round(game: Game) -> None:
    svc_score_current_round(game)

def _set_next_round_or_finish(game: Game) -> None:
    prev_round = int(game.current_round or 0)
    if game.current_round < (game.total_rounds or 0):
        game.current_round += 1
        game.stage = 'round_intro'
        try:
            order = json.loads(game.play_order or '[]')
        except Exception:
            order = []
        idx = (game.current_round - 1) if game.current_round else 0
        next_author_id = order[idx] if 0 <= idx < len(order) else None
        next_story = Story.query.filter_by(game_id=game.id, author_id=next_author_id).first() if next_author_id else None
        game.current_story_id = next_story.id if next_story else None
        try:
            current_app.logger.info(f"[next_round] game={game.id} advance round {prev_round} -> {game.current_round} author={next_author_id}")
        except Exception:
            pass
    else:
        game.status = 'finished'
        game.stage = 'finished'
        try:
            current_app.logger.info(f"[finish] game={game.id} finished at round={prev_round}")
        except Exception:
            pass
    db.session.add(game)
    db.session.commit()
    socketio.emit('state_update', {'game_code': game.game_code}, to=f"game:{game.game_code}", namespace='/ws')

def _schedule_stage_timer(app, game_id: int) -> None:
    svc_schedule_stage_timer(app, game_id)


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
    # Include stage durations so clients can show countdowns
    try:
        cfg = current_app.config
        durations = {
            'round_intro': int(cfg.get('ROUND_INTRO_DURATION_SEC', 5)),
            'guessing': int(cfg.get('GUESS_DURATION_SEC', 20)),
            'scoreboard': int(cfg.get('SCOREBOARD_DURATION_SEC', 6)),
        }
    except Exception:
        durations = {'round_intro': 5, 'guessing': 20, 'scoreboard': 6}
    payload = game.to_dict()
    payload['durations'] = durations
    return jsonify(payload)


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
    _schedule_stage_timer(current_app._get_current_object(), game.id)
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
        _schedule_stage_timer(current_app._get_current_object(), game.id)
        return jsonify(game.to_dict())

    # guessing -> scoreboard OR scoreboard -> next round/finished
    if game.current_round is None or game.total_rounds is None:
        return jsonify({'error': 'Rounds not initialized'}), 400
    if game.stage == 'guessing':
        # Score this round
        if game.current_story_id:
            story = Story.query.get(game.current_story_id)
            author = Player.query.get(story.author_id) if story else None
            if author:
                guesses = Guess.query.filter_by(story_id=game.current_story_id).all()
                # Points: +1 to each correct guesser; +1 to author for each non-author who didn't guess author (wrong or no guess)
                players = Player.query.filter_by(game_id=game.id).all()
                non_author_ids = {p.id for p in players if p.id != author.id}
                guessed_by_ids = set()
                for g in guesses:
                    guesser = Player.query.get(g.guesser_id)
                    if not guesser:
                        continue
                    guessed_by_ids.add(guesser.id)
                    if g.guessed_player_id == author.id:
                        guesser.score += 1
                        db.session.add(guesser)
                # Everyone who did not guess the author (either wrong guess or no guess) gives +1 to author
                wrong_or_missing_ids = non_author_ids - {g.guesser_id for g in guesses if g.guessed_player_id == author.id}
                if wrong_or_missing_ids:
                    author.score += len(wrong_or_missing_ids)
                    db.session.add(author)
                db.session.commit()
        game.stage = 'scoreboard'
        db.session.add(game)
        db.session.commit()
        socketio.emit('state_update', {'game_code': game.game_code}, to=f"game:{game.game_code}", namespace='/ws')
        _schedule_stage_timer(current_app._get_current_object(), game.id)
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
        _schedule_stage_timer(current_app._get_current_object(), game.id)
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
