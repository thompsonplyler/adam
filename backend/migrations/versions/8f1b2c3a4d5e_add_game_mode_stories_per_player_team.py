"""add game_mode, stories_per_player to game; team to player

Revision ID: 8f1b2c3a4d5e
Revises: d4d5eabfd23e
Create Date: 2025-08-27 15:05:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '8f1b2c3a4d5e'
down_revision = 'aaddaf18b59a'
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    insp = sa.inspect(bind)

    # If legacy plural tables detected (fresh install), no-op here; the prior migration creates singular tables.
    existing_tables = set(insp.get_table_names())
    if 'game' not in existing_tables:
        return

    # Add columns to game
    game_cols = {c['name'] for c in insp.get_columns('game')}
    if 'game_mode' not in game_cols:
        op.add_column('game', sa.Column('game_mode', sa.String(length=32), nullable=True))
        op.execute("UPDATE game SET game_mode = 'free_for_all' WHERE game_mode IS NULL")
    if 'stories_per_player' not in game_cols:
        op.add_column('game', sa.Column('stories_per_player', sa.Integer(), nullable=True))
        op.execute("UPDATE game SET stories_per_player = 1 WHERE stories_per_player IS NULL")

    # Add team to player
    if 'player' in existing_tables:
        player_cols = {c['name'] for c in insp.get_columns('player')}
        if 'team' not in player_cols:
            op.add_column('player', sa.Column('team', sa.String(length=32), nullable=True))


def downgrade():
    bind = op.get_bind()
    insp = sa.inspect(bind)

    # Drop columns from player
    player_cols = {c['name'] for c in insp.get_columns('player')}
    if 'team' in player_cols:
        op.drop_column('player', 'team')

    # Drop columns from game
    game_cols = {c['name'] for c in insp.get_columns('game')}
    if 'stories_per_player' in game_cols:
        op.drop_column('game', 'stories_per_player')
    if 'game_mode' in game_cols:
        op.drop_column('game', 'game_mode')


