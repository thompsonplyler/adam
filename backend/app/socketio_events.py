from flask_socketio import join_room, leave_room, emit
from app import socketio


def handle_connect():
    emit('connected', {'message': 'Connected to /ws'})


def handle_disconnect():
    pass


def handle_join_game(data):
    game_code = (data or {}).get('game_code')
    if not game_code:
        emit('error', {'message': 'game_code is required'})
        return
    room = f"game:{game_code.upper()}"
    join_room(room)
    emit('joined', {'room': room})


def handle_leave_game(data):
    game_code = (data or {}).get('game_code')
    if not game_code:
        emit('error', {'message': 'game_code is required'})
        return
    room = f"game:{game_code.upper()}"
    leave_room(room)
    emit('left', {'room': room})


def handle_ping(data):
    emit('pong', data or {})


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


