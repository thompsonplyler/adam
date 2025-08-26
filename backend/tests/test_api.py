def test_create_game(client):
    res = client.post('/api/games/create')
    assert res.status_code == 201
    data = res.get_json()
    assert 'game_code' in data


def test_join_and_state(client):
    # create game
    res = client.post('/api/games/create')
    code = res.get_json()['game_code']
    # join as Alice
    res = client.post('/api/games/join', json={'game_code': code, 'name': 'Alice'})
    assert res.status_code == 201
    player = res.get_json()
    # fetch state
    res = client.get(f'/api/games/{code}/state')
    assert res.status_code == 200
    game = res.get_json()
    assert game['game_code'] == code
    assert any(p['name'] == 'Alice' for p in game['players'])


def test_submit_story_and_progresses(client):
    # create game and add two players
    code = client.post('/api/games/create').get_json()['game_code']
    alice = client.post('/api/games/join', json={'game_code': code, 'name': 'Alice'}).get_json()
    bob = client.post('/api/games/join', json={'game_code': code, 'name': 'Bob'}).get_json()
    # submit one story
    res = client.post(f'/api/games/{code}/stories', json={'player_id': alice['id'], 'story': 'Once I...'} )
    assert res.status_code == 201
    # status should remain lobby until all submit
    state = client.get(f'/api/games/{code}/state').get_json()
    assert state['status'] == 'lobby'
    # submit second story
    res = client.post(f'/api/games/{code}/stories', json={'player_id': bob['id'], 'story': 'Another time...'} )
    assert res.status_code == 201
    state = client.get(f'/api/games/{code}/state').get_json()
    # Still lobby until manual start; then controller starts game
    # Simulate controller start
    controller_id = min(p['id'] for p in state['players'])
    started = client.post(f'/api/games/{code}/start', json={'controller_id': controller_id}).get_json()
    assert started['status'] == 'in_progress'
    assert started['stage'] == 'round_intro'
    assert started['current_round'] == 1
    assert started['total_rounds'] == 2
    # Advance round: round_intro -> scoreboard
    adv = client.post(f'/api/games/{code}/advance', json={'controller_id': controller_id}).get_json()
    assert adv['stage'] == 'scoreboard'
    # Advance round: scoreboard -> next round round_intro
    adv = client.post(f'/api/games/{code}/advance', json={'controller_id': controller_id}).get_json()
    assert adv['current_round'] == 2
    assert adv['stage'] == 'round_intro'
    # Advance round: round_intro -> scoreboard
    adv = client.post(f'/api/games/{code}/advance', json={'controller_id': controller_id}).get_json()
    assert adv['stage'] == 'scoreboard'
    # Advance round: last scoreboard -> finished
    adv = client.post(f'/api/games/{code}/advance', json={'controller_id': controller_id}).get_json()
    assert adv['status'] == 'finished'
    assert adv['stage'] == 'finished'


