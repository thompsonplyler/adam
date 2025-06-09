from flask import Blueprint, jsonify, request
from flask_login import login_required, current_user
from app import db
from app.models import Game, Player, Story, Guess

games = Blueprint('games', __name__)

@games.route('/create', methods=['POST'])
@login_required
def create_game():
    """
    Creates a new game lobby and adds the current user as the first player.
    """
    new_game = Game()
    db.session.add(new_game)
    db.session.commit()

    # Add the creator as the first player
    player = Player(user_id=current_user.id, game_id=new_game.id)
    db.session.add(player)
    db.session.commit()
    
    return jsonify({
        'message': 'New game created!',
        'code': new_game.game_code
    }), 201 

@games.route('/join', methods=['POST'])
@login_required
def join_game():
    """
    Allows a logged-in user to join a game using a game code.
    """
    data = request.get_json()
    game_code = data.get('game_code')
    if not game_code:
        return jsonify({'error': 'Game code is required'}), 400

    game = Game.query.filter_by(game_code=game_code.upper()).first()
    if not game:
        return jsonify({'error': 'Game not found'}), 404

    if game.status != 'lobby':
        return jsonify({'error': 'This game is not in the lobby'}), 403

    # Check if user is already in the game
    player = Player.query.filter_by(user_id=current_user.id, game_id=game.id).first()
    if player:
        return jsonify({'error': 'You are already in this game'}), 400

    new_player = Player(user_id=current_user.id, game_id=game.id)
    db.session.add(new_player)
    db.session.commit()

    return jsonify({
        'message': f'Successfully joined game {game.game_code}',
        'game_id': game.id
    }), 200 

@games.route('/<string:game_code>/start', methods=['POST'])
@login_required
def start_game(game_code):
    """
    Starts the game, changing its status from 'lobby' to 'in_progress'.
    """
    game = Game.query.filter_by(game_code=game_code.upper()).first_or_404()

    # Optional: Add logic to ensure only the game creator can start
    player = Player.query.filter_by(user_id=current_user.id, game_id=game.id).first()
    if not player:
        return jsonify({'error': 'You are not a player in this game'}), 403

    if game.status != 'lobby':
        return jsonify({'error': 'Game has already started or is finished'}), 400

    game.status = 'in_progress'
    db.session.commit()

    return jsonify({'message': f'Game {game.game_code} has started!'}), 200

@games.route('/<string:game_code>/story', methods=['GET'])
@login_required
def get_next_story(game_code):
    """
    Fetches a random, unread story for the current game round.
    """
    game = Game.query.filter_by(game_code=game_code.upper()).first_or_404()

    if game.status != 'in_progress':
        return jsonify({'error': 'This game is not currently in progress'}), 403

    # Find an unread story
    next_story = Story.query.filter_by(game_id=game.id, is_read=False).order_by(db.func.random()).first()

    if not next_story:
        game.status = 'finished'
        db.session.commit()
        return jsonify({'message': 'No more stories to read! Game over.'}), 200

    # Set it as the current story and mark it as read
    game.current_story_id = next_story.id
    next_story.is_read = True
    db.session.commit()

    return jsonify({
        'story_id': next_story.id,
        'content': next_story.content
    }), 200

@games.route('/<string:game_code>/guess', methods=['POST'])
@login_required
def submit_guess(game_code):
    """
    Submits a guess for the current story's author.
    """
    game = Game.query.filter_by(game_code=game_code.upper()).first_or_404()
    if not game.current_story_id:
        return jsonify({'error': 'There is no active story to guess on'}), 400

    data = request.get_json()
    guessed_user_id = data.get('guessed_user_id')
    if not guessed_user_id:
        return jsonify({'error': 'Guessed user ID is required'}), 400

    # Verify the current user is a player in this game
    if not any(p.user_id == current_user.id for p in game.players):
        return jsonify({'error': 'You are not a player in this game'}), 403
        
    # Prevent user from guessing themselves
    if current_user.id == guessed_user_id:
        return jsonify({'error': 'You cannot guess yourself'}), 400

    # Check if the user has already guessed for this story
    existing_guess = Guess.query.filter_by(
        story_id=game.current_story_id,
        guesser_id=current_user.id
    ).first()
    if existing_guess:
        return jsonify({'error': 'You have already guessed for this story'}), 400

    new_guess = Guess(
        story_id=game.current_story_id,
        guesser_id=current_user.id,
        guessed_id=guessed_user_id
    )
    db.session.add(new_guess)
    db.session.commit()

    return jsonify({'message': 'Guess submitted successfully'}), 201

@games.route('/<string:game_code>/results', methods=['GET'])
@login_required
def get_results(game_code):
    """
    Calculates and returns the results for the current story round.
    """
    game = Game.query.filter_by(game_code=game_code.upper()).first_or_404()
    if not game.current_story_id:
        return jsonify({'error': 'There is no active story to get results for'}), 400

    story = Story.query.get(game.current_story_id)
    author = story.author
    guesses = Guess.query.filter_by(story_id=story.id).all()

    round_scores = {}

    # 2 points for each correct guess
    for guess in guesses:
        player = Player.query.filter_by(user_id=guess.guesser_id, game_id=game.id).first()
        if guess.guessed_id == author.id:
            player.score += 2
            round_scores[player.user.username] = round_scores.get(player.user.username, 0) + 2
    
    # 1 point for each person the author fooled
    author_player = Player.query.filter_by(user_id=author.id, game_id=game.id).first()
    for guess in guesses:
        if guess.guessed_id != author.id:
            author_player.score += 1
            round_scores[author.username] = round_scores.get(author.username, 0) + 1

    db.session.commit()

    return jsonify({
        'message': 'Round results',
        'true_author': author.username,
        'round_scores': round_scores,
        'total_scores': {p.user.username: p.score for p in game.players}
    }), 200

@games.route('/stories/submit', methods=['POST'])
@login_required
def submit_story():
    """
    Allows a player to submit a story to a game they have joined.
    """
    data = request.get_json()
    game_id = data.get('game_id')
    content = data.get('content')

    if not all([game_id, content]):
        return jsonify({'error': 'Game ID and story content are required'}), 400

    # Verify the user is a player in this game
    player = Player.query.filter_by(user_id=current_user.id, game_id=game_id).first()
    if not player:
        return jsonify({'error': 'You are not a player in this game'}), 403
    
    # Optional: Add logic to check game status (e.g., only submit during 'lobby' or 'story_submission' phase)
    # Optional: Add logic to limit the number of stories per player based on game_length

    new_story = Story(
        content=content,
        author_id=current_user.id,
        game_id=game_id
    )
    db.session.add(new_story)
    db.session.commit()

    return jsonify({
        'message': 'Story submitted successfully',
        'story_id': new_story.id
    }), 201 

@games.route('/<string:game_code>/state', methods=['GET'])
@login_required
def get_game_state(game_code):
    """
    Returns the full state of a game.
    """
    game = Game.query.filter_by(game_code=game_code.upper()).first_or_404()
    if not any(p.user_id == current_user.id for p in game.players):
        return jsonify({'error': 'You are not a player in this game'}), 403

    stories_submitted = [s.author_id for s in game.stories]
    
    players = []
    for p in game.players:
        players.append({
            'id': p.user.id,
            'username': p.user.username,
            'score': p.score,
            'has_submitted': p.user.id in stories_submitted
        })

    response = {
        'id': game.id,
        'game_code': game.game_code,
        'status': game.status,
        'players': players,
        'is_creator': game.players[0].user_id == current_user.id # Simple assumption for now
    }

    if game.current_story:
        response['current_story'] = {
            'id': game.current_story.id,
            'content': game.current_story.content
        }

    return jsonify(response), 200 

@games.route('/active', methods=['GET'])
@login_required
def get_active_games():
    """
    Returns a list of active games the user is part of.
    """
    player_entries = Player.query.filter_by(user_id=current_user.id).all()
    active_games = []
    for entry in player_entries:
        if entry.game.status in ['lobby', 'in_progress']:
            active_games.append({'game_code': entry.game.game_code})
    
    return jsonify(active_games), 200 

@games.route('/<string:game_code>/leave', methods=['POST'])
@login_required
def leave_game(game_code):
    """
    Removes the current user from a game. If the last player leaves,
    the game and all related data is deleted.
    """
    game = Game.query.filter_by(game_code=game_code.upper()).first_or_404()
    player = Player.query.filter_by(user_id=current_user.id, game_id=game.id).first()

    if not player:
        return jsonify({'error': 'You are not in this game'}), 404

    db.session.delete(player)

    # Check if the game is now empty
    if not game.players:
        # Nullify the foreign key constraint before deleting stories
        game.current_story_id = None
        db.session.commit()

        # Delete all guesses associated with the game's stories first
        story_ids = [s.id for s in game.stories]
        Guess.query.filter(Guess.story_id.in_(story_ids)).delete(synchronize_session=False)
        # Delete all stories
        Story.query.filter_by(game_id=game.id).delete()
        # Delete the game itself
        db.session.delete(game)
        
    db.session.commit()
    return jsonify({'message': 'You have left the game.'}), 200 