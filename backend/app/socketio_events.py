from flask_socketio import join_room, leave_room, emit
from app import socketio, db
from flask import current_app
from app.models import Game, Player, Story, Guess
from typing import Dict, Any
import time


def handle_connect():
    emit('connected', {'message': 'Connected to /ws'})


def handle_disconnect():
    # On disconnect, if this socket was a host for a room and no other
    # host remains, end the session for that game code
    ctx = _sid_to_ctx.pop(_get_sid(), None)
    if not ctx:
        return
    game_code = ctx.get('game_code')
    if ctx.get('is_session_owner') and game_code:
        _owner_count[game_code] = max(0, _owner_count.get(game_code, 0) - 1)
        # In tests, end immediately for determinism; in prod, allow grace period
        try:
            if current_app and current_app.config.get('TESTING'):
                if _owner_count.get(game_code, 0) == 0:
                    _end_session(game_code)
                return
        except Exception:
            pass
        _schedule_end_if_no_owner(game_code)


def handle_join_game(data):
    game_code = (data or {}).get('game_code')
    is_session_owner = bool((data or {}).get('is_session_owner'))
    if not game_code:
        emit('error', {'message': 'game_code is required'})
        return
    room = f"game:{game_code.upper()}"
    join_room(room)
    # Track session owner presence and socket context
    _sid_to_ctx[_get_sid()] = {'game_code': game_code.upper(), 'is_session_owner': is_session_owner}
    if is_session_owner:
        _owner_count[game_code.upper()] = _owner_count.get(game_code.upper(), 0) + 1
        _cancel_scheduled_end(game_code.upper())
    emit('joined', {'room': room})


def handle_leave_game(data):
    game_code = (data or {}).get('game_code')
    if not game_code:
        emit('error', {'message': 'game_code is required'})
        return
    room = f"game:{game_code.upper()}"
    leave_room(room)
    emit('left', {'room': room})
    # If a session owner leaves explicitly, decrement and possibly end session
    ctx = _sid_to_ctx.get(_get_sid())
    if ctx and ctx.get('is_session_owner') and ctx.get('game_code') == game_code.upper():
        # Explicit quit: end immediately
        _end_session(game_code.upper())


def handle_ping(data):
    emit('pong', data or {})

# ---- Session owner lifecycle helpers ----
from flask import request
from flask_socketio import rooms

_sid_to_ctx: Dict[str, Dict[str, Any]] = {}
_owner_count: Dict[str, int] = {}
_end_deadline: Dict[str, float] = {}

def _get_sid() -> str:
    # type: ignore: request.sid exists in Socket.IO context
    return request.sid  # type: ignore

def _end_session(game_code: str) -> None:
    """End the session: notify clients and cleanup DB rows for the game."""
    # Use socketio.emit since this may be called from a background task
    socketio.emit('session_ended', {'game_code': game_code}, room=f"game:{game_code}", namespace='/ws')
    try:
        game = Game.query.filter_by(game_code=game_code).first()
        if game:
            # Break FK from game to story to avoid violations
            if getattr(game, 'current_story_id', None):
                game.current_story_id = None
                db.session.add(game)
                db.session.commit()
            # Clean dependent rows
            try:
                for story in list(game.stories) if hasattr(game.stories, '__iter__') else []:
                    Guess.query.filter_by(story_id=story.id).delete()
            except Exception:
                # If relationship is dynamic, skip iteration and rely on bulk deletes
                pass
            Story.query.filter_by(game_id=game.id).delete()
            Player.query.filter_by(game_id=game.id).delete()
            db.session.delete(game)
            db.session.commit()
    except Exception:
        db.session.rollback()
    finally:
        _owner_count.pop(game_code, None)
        _end_deadline.pop(game_code, None)

def _schedule_end_if_no_owner(game_code: str, delay_sec: float = 2.0) -> None:
    if _owner_count.get(game_code, 0) > 0:
        return
    _end_deadline[game_code] = time.time() + delay_sec

    def _runner(code: str, deadline: float):
        sleep_for = max(0.0, deadline - time.time())
        if sleep_for:
            time.sleep(sleep_for)
        if _owner_count.get(code, 0) == 0 and _end_deadline.get(code) == deadline:
            _end_session(code)

    try:
        socketio.start_background_task(_runner, game_code, _end_deadline[game_code])
    except Exception:
        _runner(game_code, _end_deadline[game_code])

def _cancel_scheduled_end(game_code: str) -> None:
    _end_deadline.pop(game_code, None)
    


def register_socketio_handlers(testing: bool = False) -> None:
    """Register Socket.IO event handlers.

    Always register on namespace '/ws'. When testing is True, also mirror
    handlers on the default namespace '/' to accommodate the test harness.
    """
    # Primary namespace
    socketio.on_event('connect', handle_connect, namespace='/ws')
    socketio.on_event('disconnect', handle_disconnect, namespace='/ws')
    socketio.on_event('join_game', handle_join_game, namespace='/ws')
    socketio.on_event('leave_game', handle_leave_game, namespace='/ws')
    socketio.on_event('ping', handle_ping, namespace='/ws')

    if testing:
        # Test-only mirror on default namespace
        socketio.on_event('connect', handle_connect, namespace='/')
        socketio.on_event('disconnect', handle_disconnect, namespace='/')
        socketio.on_event('join_game', handle_join_game, namespace='/')
        socketio.on_event('leave_game', handle_leave_game, namespace='/')
        socketio.on_event('ping', handle_ping, namespace='/')


