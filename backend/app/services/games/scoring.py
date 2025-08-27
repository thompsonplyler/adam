from app import db
from app.models import Game, Player, Story, Guess

def score_current_round(game: Game) -> None:
    """Apply scoring for the current round.

    +1 to each correct guesser; +1 to author for each non-author who didn't
    pick the author (wrong guess or no guess).
    """
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



