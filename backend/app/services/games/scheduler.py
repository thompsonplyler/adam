import time
import json
from typing import Set, Tuple

from app import db, socketio
from app.models import Game, Story
from .scoring import score_current_round


_scheduled_stage_keys: Set[Tuple[int, str, int]] = set()


def schedule_stage_timer(app, game_id: int) -> None:
    """Schedule auto-advance for the current stage of the given game.

    - No-ops in TESTING mode
    - Sets game.stage_deadline so clients can render countdowns
    - Ensures a single timer per (game_id, stage, round)
    - Advances through the pipeline: round_intro -> guessing -> scoreboard -> next/finished
    """
    if app.config.get('TESTING'):
        return

    with app.app_context():
        game = Game.query.filter_by(id=game_id).first()
        if not game or game.status != 'in_progress' or not game.stage:
            return

        stage = game.stage
        round_idx = int(game.current_round or 0)
        key = (game.id, stage, round_idx)

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

        # Expose a client-visible deadline for countdowns
        try:
            game.stage_deadline = time.time() + duration
            db.session.add(game)
            db.session.commit()
        except Exception:
            db.session.rollback()

        try:
            app.logger.info(
                f"[timer-set] game={game.id} stage={stage} round={round_idx} duration={duration}s deadline={game.stage_deadline}"
            )
        except Exception:
            pass

    def _worker(expected_stage: str, gid: int, expected_round: int, delay: int):
        time.sleep(delay)
        with app.app_context():
            g = Game.query.filter_by(id=gid).first()
            _scheduled_stage_keys.discard((gid, expected_stage, expected_round))
            if not g:
                return
            try:
                app.logger.info(
                    f"[timer-fire] game={gid} expected_stage={expected_stage} expected_round={expected_round} actual_stage={g.stage} actual_round={g.current_round}"
                )
            except Exception:
                pass

            if g.status != 'in_progress' or g.stage != expected_stage or int(g.current_round or 0) != expected_round:
                try:
                    app.logger.info(f"[timer-abort] game={gid} mismatch status/stage/round")
                except Exception:
                    pass
                return

            # Perform stage transition
            if expected_stage == 'round_intro':
                g.stage = 'guessing'
                db.session.add(g)
                db.session.commit()
                socketio.emit('state_update', {'game_code': g.game_code}, to=f"game:{g.game_code}", namespace='/ws')
                schedule_stage_timer(app, g.id)
                return

            if expected_stage == 'guessing':
                score_current_round(g)
                g.stage = 'scoreboard'
                db.session.add(g)
                db.session.commit()
                socketio.emit('state_update', {'game_code': g.game_code}, to=f"game:{g.game_code}", namespace='/ws')
                schedule_stage_timer(app, g.id)
                return

            if expected_stage == 'scoreboard':
                if g.current_round < (g.total_rounds or 0):
                    g.current_round += 1
                    g.stage = 'round_intro'
                    try:
                        order = json.loads(g.play_order or '[]')
                    except Exception:
                        order = []
                    idx = (g.current_round - 1) if g.current_round else 0
                    next_author_id = order[idx] if 0 <= idx < len(order) else None
                    next_story = (
                        Story.query.filter_by(game_id=g.id, author_id=next_author_id).first() if next_author_id else None
                    )
                    g.current_story_id = next_story.id if next_story else None
                else:
                    g.status = 'finished'
                    g.stage = 'finished'
                db.session.add(g)
                db.session.commit()
                socketio.emit('state_update', {'game_code': g.game_code}, to=f"game:{g.game_code}", namespace='/ws')
                if g.status == 'in_progress':
                    schedule_stage_timer(app, g.id)
                return

    socketio.start_background_task(_worker, stage, game.id, round_idx, duration)


