def test_socket_connect_and_join(sio_client):
    # Ensure we are connected to /ws
    if not sio_client.is_connected('/ws'):
        sio_client.connect(namespace='/ws')
    assert sio_client.is_connected('/ws')

    # Flush any initial events
    try:
        sio_client.get_received('/ws')
    except Exception:
        pass

    # Join a room and expect a joined ack
    sio_client.emit('join_game', {'game_code': 'ABCD'}, namespace='/ws')
    received = sio_client.get_received('/ws')
    assert any(pkt['name'] in ('connected', 'joined') for pkt in received)


def test_host_disconnect_ends_session(flask_app, sio_client, client):
    # Create a game via HTTP
    res = client.post('/api/games/create')
    code = res.get_json()['game_code']

    # Connect as host and guest
    if not sio_client.is_connected('/ws'):
        sio_client.connect(namespace='/ws')
    # A separate client to simulate host
    from app import socketio as _sio
    host_client = _sio.test_client(flask_app, namespace='/ws')
    host_client.emit('join_game', {'game_code': code, 'is_session_owner': True}, namespace='/ws')

    # Guest joins
    sio_client.emit('join_game', {'game_code': code}, namespace='/ws')
    sio_client.get_received('/ws')  # flush

    # Disconnect host -> expect session_ended for guest
    host_client.disconnect(namespace='/ws')
    # Allow grace period for session owner disconnect handling
    import time
    deadline = time.time() + 3.0
    got = False
    while time.time() < deadline and not got:
        events = sio_client.get_received('/ws')
        got = any(e['name'] == 'session_ended' for e in events)
        if not got:
            time.sleep(0.1)
    assert got


