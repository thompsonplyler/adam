from flask import Blueprint, jsonify, request, current_app
from app import db, socketio
from app.models import Game, Player, Story, Guess
import json
import time
from typing import Set, Tuple


games = Blueprint('games', __name__)

# Centralized stage timer scheduler (runtime-only; disabled in tests)
_scheduled_stage_keys: Set[Tuple[int, str, int]] = set()

def _score_current_round(game: Game) -> None:
    if not game.current_story_id:
        return
    story = Story.query.get(game.current_story_id)
    author = Player.query.get(story.author_id) if story else None
    if not author:
        return
    guesses = Guess.query.filter_by(story_id=game.current_story_id).all()
    players = Player.query.filter_by(game_id=game.id).all()
    non_author_ids = {p.id for p in players if p.id != author.id}
    for g in guesses:
        guesser = Player.query.get(g.guesser_id)
        if not guesser:
            continue
        if g.guessed_player_id == author.id:
            guesser.score += 1
            db.session.add(guesser)
    wrong_or_missing_ids = non_author_ids - {g.guesser_id for g in guesses if g.guessed_player_id == author.id}
    if wrong_or_missing_ids:
        author.score += len(wrong_or_missing_ids)
        db.session.add(author)
    db.session.commit()
    try:
        current_app.logger.info(f"[score] game={game.id} round={game.current_round} scored: author={author.id if author else 'n/a'} correct={len(guesses) - len(wrong_or_missing_ids)} wrong_or_missing={len(wrong_or_missing_ids)}")
    except Exception:
        pass

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
    if app.config.get('TESTING'):
        return
    with app.app_context():
        game = Game.query.filter_by(id=game_id).first()
        if not game or game.status != 'in_progress' or not game.stage:
            return
        stage = game.stage
        round_idx = int(game.current_round or 0)
        key = (game.id, stage, round_idx)
        # Determine duration
        if stage == 'round_intro':
            duration = int(app.config.get('ROUND_INTRO_DURATION_SEC', 5))
        elif stage == 'guessing':
            duration = int(app.config.get('GUESS_DURATION_SEC', 20))
        elif stage == 'scoreboard':
            duration = int(app.config.get('SCOREBOARD_DURATION_SEC', 6))
        else:
            return
        if key in _scheduled_stage_keys:
            try:
                app.logger.info(f"[timer-skip] game={game.id} stage={stage} round={round_idx} already scheduled")
            except Exception:
                pass
            return
        _scheduled_stage_keys.add(key)
        try:
            app.logger.info(f"[timer-set] game={game.id} stage={stage} round={round_idx} duration={duration}s")
        except Exception:
            pass

    def _worker(expected_stage: str, gid: int, expected_round: int):
        time.sleep(duration)
        with app.app_context():
            g = Game.query.filter_by(id=gid).first()
            _scheduled_stage_keys.discard((gid, expected_stage, expected_round))
            if not g:
                return
            try:
                app.logger.info(f"[timer-fire] game={gid} expected_stage={expected_stage} expected_round={expected_round} actual_stage={g.stage} actual_round={g.current_round}")
            except Exception:
                pass
            if g.status != 'in_progress' or g.stage != expected_stage or int(g.current_round or 0) != expected_round:
                try:
                    app.logger.info(f"[timer-abort] game={gid} mismatch status/stage/round")
                except Exception:
                    pass
                return
            if expected_stage == 'round_intro':
                g.stage = 'guessing'
                db.session.add(g)
                db.session.commit()
                socketio.emit('state_update', {'game_code': g.game_code}, to=f"game:{g.game_code}", namespace='/ws')
                _schedule_stage_timer(app, g.id)
                return
            if expected_stage == 'guessing':
                _score_current_round(g)
                g.stage = 'scoreboard'
                db.session.add(g)
                db.session.commit()
                socketio.emit('state_update', {'game_code': g.game_code}, to=f"game:{g.game_code}", namespace='/ws')
                _schedule_stage_timer(app, g.id)
                return
            if expected_stage == 'scoreboard':
                _set_next_round_or_finish(g)
                if g.status == 'in_progress':
                    _schedule_stage_timer(app, g.id)
                return

    socketio.start_background_task(_worker, stage, game.id, int(game.current_round or 0))


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
    # Schedule auto-advance from initial round_intro to guessing after intro duration
    _schedule_stage_timer(current_app._get_current_object(), game.id)
    try:
        app = current_app._get_current_object()
        intro_dur = int(app.config.get('ROUND_INTRO_DURATION_SEC', 5))
        def _intro_start():
            with app.app_context():
                g4 = Game.query.filter_by(id=game.id).first()
                if g4 and g4.status == 'in_progress' and g4.stage == 'round_intro':
                    g4.stage = 'guessing'
                    db.session.add(g4)
                    db.session.commit()
                    socketio.emit('state_update', {'game_code': g4.game_code}, to=f"game:{g4.game_code}", namespace='/ws')
                    # Chain guessing timer from here as well
                    try:
                        duration = int(app.config.get('GUESS_DURATION_SEC', 20))
                        def _adv2():
                            with app.app_context():
                                g2 = Game.query.filter_by(id=g4.id).first()
                                if g2 and g2.status == 'in_progress' and g2.stage == 'guessing':
                                    # Score and move to scoreboard
                                    if g2.current_story_id:
                                        story = Story.query.get(g2.current_story_id)
                                        author = Player.query.get(story.author_id) if story else None
                                        if author:
                                            guesses = Guess.query.filter_by(story_id=g2.current_story_id).all()
                                            players2 = Player.query.filter_by(game_id=g2.id).all()
                                            non_author_ids2 = {p.id for p in players2 if p.id != author.id}
                                            for gu in guesses:
                                                guesser = Player.query.get(gu.guesser_id)
                                                if not guesser:
                                                    continue
                                                if gu.guessed_player_id == author.id:
                                                    guesser.score += 1
                                                    db.session.add(guesser)
                                            wrong_or_missing_ids2 = non_author_ids2 - {gu.guesser_id for gu in guesses if gu.guessed_player_id == author.id}
                                            if wrong_or_missing_ids2:
                                                author.score += len(wrong_or_missing_ids2)
                                                db.session.add(author)
                                            db.session.commit()
                                    g2.stage = 'scoreboard'
                                    db.session.add(g2)
                                    db.session.commit()
                                    socketio.emit('state_update', {'game_code': g2.game_code}, to=f"game:{g2.game_code}", namespace='/ws')
                                    # Schedule scoreboard auto-advance for first round path
                                    try:
                                        sb_dur0 = int(app.config.get('SCOREBOARD_DURATION_SEC', 6))
                                        def _sb0():
                                            with app.app_context():
                                                g3 = Game.query.filter_by(id=g2.id).first()
                                                if not g3 or g3.status != 'in_progress' or g3.stage != 'scoreboard':
                                                    return
                                                if g3.current_round < (g3.total_rounds or 0):
                                                    g3.current_round += 1
                                                    g3.stage = 'round_intro'
                                                    try:
                                                        order = json.loads(g3.play_order or '[]')
                                                    except Exception:
                                                        order = []
                                                    idx = (g3.current_round - 1) if g3.current_round else 0
                                                    next_author_id = order[idx] if 0 <= idx < len(order) else None
                                                    next_story = Story.query.filter_by(game_id=g3.id, author_id=next_author_id).first() if next_author_id else None
                                                    g3.current_story_id = next_story.id if next_story else None
                                                else:
                                                    g3.status = 'finished'
                                                    g3.stage = 'finished'
                                                db.session.add(g3)
                                                db.session.commit()
                                                socketio.emit('state_update', {'game_code': g3.game_code}, to=f"game:{g3.game_code}", namespace='/ws')
                                        socketio.start_background_task(lambda: (time.sleep(sb_dur0), _sb0()))
                                    except Exception:
                                        pass
                    
                        socketio.start_background_task(lambda: (time.sleep(duration), _adv2()))
                    except Exception:
                        pass
        socketio.start_background_task(lambda: (time.sleep(intro_dur), _intro_start()))
    except Exception:
        pass
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
        # Schedule auto-advance to scoreboard after guess duration
        try:
            duration = int(current_app.config.get('GUESS_DURATION_SEC', 20))
            app = current_app._get_current_object()
            def _adv():
                with app.app_context():
                    g2 = Game.query.filter_by(id=game.id).first()
                    if g2 and g2.status == 'in_progress' and g2.stage == 'guessing':
                        # Reuse pipeline: pretend controller calls advance to score
                        # Score logic is inside the guessing branch; call directly here
                        if g2.current_story_id:
                            story = Story.query.get(g2.current_story_id)
                            author = Player.query.get(story.author_id) if story else None
                            if author:
                                guesses = Guess.query.filter_by(story_id=g2.current_story_id).all()
                                players = Player.query.filter_by(game_id=g2.id).all()
                                non_author_ids = {p.id for p in players if p.id != author.id}
                                for g in guesses:
                                    guesser = Player.query.get(g.guesser_id)
                                    if not guesser:
                                        continue
                                    if g.guessed_player_id == author.id:
                                        guesser.score += 1
                                        db.session.add(guesser)
                                wrong_or_missing_ids = non_author_ids - {g.guesser_id for g in guesses if g.guessed_player_id == author.id}
                                if wrong_or_missing_ids:
                                    author.score += len(wrong_or_missing_ids)
                                    db.session.add(author)
                                db.session.commit()
                        g2.stage = 'scoreboard'
                        db.session.add(g2)
                        db.session.commit()
                        socketio.emit('state_update', {'game_code': g2.game_code}, to=f"game:{g2.game_code}", namespace='/ws')
                        # Schedule scoreboard auto-advance
                        try:
                            sb_dur = int(app.config.get('SCOREBOARD_DURATION_SEC', 6))
                            def _sb():
                                with app.app_context():
                                    g3 = Game.query.filter_by(id=g2.id).first()
                                    if not g3 or g3.status != 'in_progress' or g3.stage != 'scoreboard':
                                        return
                                    if g3.current_round < (g3.total_rounds or 0):
                                        g3.current_round += 1
                                        g3.stage = 'round_intro'
                                        try:
                                            order = json.loads(g3.play_order or '[]')
                                        except Exception:
                                            order = []
                                        idx = (g3.current_round - 1) if g3.current_round else 0
                                        next_author_id = order[idx] if 0 <= idx < len(order) else None
                                        next_story = Story.query.filter_by(game_id=g3.id, author_id=next_author_id).first() if next_author_id else None
                                        g3.current_story_id = next_story.id if next_story else None
                                    else:
                                        g3.status = 'finished'
                                        g3.stage = 'finished'
                                    db.session.add(g3)
                                    db.session.commit()
                                    socketio.emit('state_update', {'game_code': g3.game_code}, to=f"game:{g3.game_code}", namespace='/ws')
                                    _schedule_stage_timer(app, g3.id)
                        except Exception:
                            pass
            socketio.start_background_task(lambda: (time.sleep(duration), _adv()))
        except Exception:
            pass
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
        # Schedule scoreboard auto-advance when reaching scoreboard via manual Next
        try:
            app = current_app._get_current_object()
            sb_dur = int(app.config.get('SCOREBOARD_DURATION_SEC', 6))
            def _sb_manual():
                with app.app_context():
                    g3 = Game.query.filter_by(id=game.id).first()
                    if not g3 or g3.status != 'in_progress' or g3.stage != 'scoreboard':
                        return
                    if g3.current_round < (g3.total_rounds or 0):
                        g3.current_round += 1
                        g3.stage = 'round_intro'
                        try:
                            order = json.loads(g3.play_order or '[]')
                        except Exception:
                            order = []
                        idx = (g3.current_round - 1) if g3.current_round else 0
                        next_author_id = order[idx] if 0 <= idx < len(order) else None
                        next_story = Story.query.filter_by(game_id=g3.id, author_id=next_author_id).first() if next_author_id else None
                        g3.current_story_id = next_story.id if next_story else None
                    else:
                        g3.status = 'finished'
                        g3.stage = 'finished'
                    db.session.add(g3)
                    db.session.commit()
                    socketio.emit('state_update', {'game_code': g3.game_code}, to=f"game:{g3.game_code}", namespace='/ws')
            socketio.start_background_task(lambda: (time.sleep(sb_dur), _sb_manual()))
        except Exception:
            pass
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
        # Schedule auto-advance from round_intro to guessing after intro duration
        try:
            app = current_app._get_current_object()
            intro_dur = int(app.config.get('ROUND_INTRO_DURATION_SEC', 5))
            def _intro():
                with app.app_context():
                    g4 = Game.query.filter_by(id=game.id).first()
                    if g4 and g4.status == 'in_progress' and g4.stage == 'round_intro':
                        g4.stage = 'guessing'
                        db.session.add(g4)
                        db.session.commit()
                        socketio.emit('state_update', {'game_code': g4.game_code}, to=f"game:{g4.game_code}", namespace='/ws')
                        # Chain guessing timer from here as well
                        try:
                            duration = int(app.config.get('GUESS_DURATION_SEC', 20))
                            def _adv2():
                                with app.app_context():
                                    g2 = Game.query.filter_by(id=g4.id).first()
                                    if g2 and g2.status == 'in_progress' and g2.stage == 'guessing':
                                        # Score and move to scoreboard (reuse logic above)
                                        if g2.current_story_id:
                                            story = Story.query.get(g2.current_story_id)
                                            author = Player.query.get(story.author_id) if story else None
                                            if author:
                                                guesses = Guess.query.filter_by(story_id=g2.current_story_id).all()
                                                players = Player.query.filter_by(game_id=g2.id).all()
                                                non_author_ids = {p.id for p in players if p.id != author.id}
                                                for g in guesses:
                                                    guesser = Player.query.get(g.guesser_id)
                                                    if not guesser:
                                                        continue
                                                    if g.guessed_player_id == author.id:
                                                        guesser.score += 1
                                                        db.session.add(guesser)
                                                wrong_or_missing_ids = non_author_ids - {g.guesser_id for g in guesses if g.guessed_player_id == author.id}
                                                if wrong_or_missing_ids:
                                                    author.score += len(wrong_or_missing_ids)
                                                    db.session.add(author)
                                                db.session.commit()
                                        g2.stage = 'scoreboard'
                                        db.session.add(g2)
                                        db.session.commit()
                                        socketio.emit('state_update', {'game_code': g2.game_code}, to=f"game:{g2.game_code}", namespace='/ws')
                                        # Schedule scoreboard auto-advance for this path as well
                                        try:
                                            sb_dur2 = int(app.config.get('SCOREBOARD_DURATION_SEC', 6))
                                            def _sb2():
                                                with app.app_context():
                                                    g3 = Game.query.filter_by(id=g2.id).first()
                                                    if not g3 or g3.status != 'in_progress' or g3.stage != 'scoreboard':
                                                        return
                                                    if g3.current_round < (g3.total_rounds or 0):
                                                        g3.current_round += 1
                                                        g3.stage = 'round_intro'
                                                        try:
                                                            order = json.loads(g3.play_order or '[]')
                                                        except Exception:
                                                            order = []
                                                        idx = (g3.current_round - 1) if g3.current_round else 0
                                                        next_author_id = order[idx] if 0 <= idx < len(order) else None
                                                        next_story = Story.query.filter_by(game_id=g3.id, author_id=next_author_id).first() if next_author_id else None
                                                        g3.current_story_id = next_story.id if next_story else None
                                                    else:
                                                        g3.status = 'finished'
                                                        g3.stage = 'finished'
                                                    db.session.add(g3)
                                                    db.session.commit()
                                                    socketio.emit('state_update', {'game_code': g3.game_code}, to=f"game:{g3.game_code}", namespace='/ws')
                                                    _schedule_stage_timer(app, g3.id)
                                        except Exception:
                                            pass
                        
                            socketio.start_background_task(lambda: (time.sleep(duration), _adv2()))
                        except Exception:
                            pass
            socketio.start_background_task(lambda: (time.sleep(intro_dur), _intro()))
        except Exception:
            pass
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
