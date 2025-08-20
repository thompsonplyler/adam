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


