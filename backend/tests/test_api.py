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
    # Advance: round_intro -> guessing
    adv = client.post(f'/api/games/{code}/advance', json={'controller_id': controller_id}).get_json()
    assert adv['stage'] == 'guessing'
    # Advance: guessing -> scoreboard
    adv = client.post(f'/api/games/{code}/advance', json={'controller_id': controller_id}).get_json()
    assert adv['stage'] == 'scoreboard'
    # Advance: scoreboard -> next round round_intro
    adv = client.post(f'/api/games/{code}/advance', json={'controller_id': controller_id}).get_json()
    assert adv['current_round'] == 2
    assert adv['stage'] == 'round_intro'
    # Advance: round 2 round_intro -> guessing
    adv = client.post(f'/api/games/{code}/advance', json={'controller_id': controller_id}).get_json()
    assert adv['stage'] == 'guessing'
    # Advance: guessing -> scoreboard (round 2)
    adv = client.post(f'/api/games/{code}/advance', json={'controller_id': controller_id}).get_json()
    assert adv['stage'] == 'scoreboard'
    # Advance: last scoreboard -> finished
    adv = client.post(f'/api/games/{code}/advance', json={'controller_id': controller_id}).get_json()
    assert adv['status'] == 'finished'
    assert adv['stage'] == 'finished'


def test_guess_and_scoring_flow(client):
    # create game and add three players for richer guessing
    code = client.post('/api/games/create').get_json()['game_code']
    a = client.post('/api/games/join', json={'game_code': code, 'name': 'Alice'}).get_json()
    b = client.post('/api/games/join', json={'game_code': code, 'name': 'Bob'}).get_json()
    c = client.post('/api/games/join', json={'game_code': code, 'name': 'Cara'}).get_json()

    # submit stories
    assert client.post(f'/api/games/{code}/stories', json={'player_id': a['id'], 'story': 'A story'}).status_code == 201
    assert client.post(f'/api/games/{code}/stories', json={'player_id': b['id'], 'story': 'B story'}).status_code == 201
    assert client.post(f'/api/games/{code}/stories', json={'player_id': c['id'], 'story': 'C story'}).status_code == 201

    # start game by controller (lowest id)
    state = client.get(f'/api/games/{code}/state').get_json()
    controller_id = min(p['id'] for p in state['players'])
    started = client.post(f'/api/games/{code}/start', json={'controller_id': controller_id}).get_json()
    assert started['status'] == 'in_progress'
    assert started['stage'] == 'round_intro'

    # advance to guessing
    adv = client.post(f'/api/games/{code}/advance', json={'controller_id': controller_id}).get_json()
    assert adv['stage'] == 'guessing'

    # Determine author (first in play_order)
    play_order = adv['play_order']
    author_id = play_order[0]
    non_authors = [p['id'] for p in adv['players'] if p['id'] != author_id]
    correct_guesser = non_authors[0]
    incorrect_guesser = non_authors[1] if len(non_authors) > 1 else None

    # submit guesses: one correct, one incorrect (if possible)
    assert client.post(f'/api/games/{code}/guess', json={'guesser_id': correct_guesser, 'guessed_player_id': author_id}).status_code == 200
    if incorrect_guesser is not None:
        wrong_target = author_id
        for pid in [a['id'], b['id'], c['id']]:
            if pid not in (author_id, incorrect_guesser):
                wrong_target = pid
                break
        assert client.post(f'/api/games/{code}/guess', json={'guesser_id': incorrect_guesser, 'guessed_player_id': wrong_target}).status_code == 200

    # move to scoreboard to score round
    adv2 = client.post(f'/api/games/{code}/advance', json={'controller_id': controller_id}).get_json()
    assert adv2['stage'] == 'scoreboard'

    # verify scores: correct guesser +1; author +1 per each non-author who didn't pick author (wrong or no guess)
    scored = client.get(f'/api/games/{code}/state').get_json()
    players = {p['id']: p for p in scored['players']}
    assert players[correct_guesser]['score'] == 1
    if incorrect_guesser is not None:
        assert players[author_id]['score'] >= 1
    else:
        # Two non-authors: if only one guessed correctly, the author should have 1 point
        assert players[author_id]['score'] == 1


