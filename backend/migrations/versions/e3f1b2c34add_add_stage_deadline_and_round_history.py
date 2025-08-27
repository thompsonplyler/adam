"""add stage_deadline and round_history to game

Revision ID: e3f1b2c34add
Revises: d4d5eabfd23e
Create Date: 2025-08-27 00:00:00
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'e3f1b2c34add'
down_revision = 'aaddaf18b59a'
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    insp = sa.inspect(bind)
    cols = {c['name'] for c in insp.get_columns('game')}
    with op.batch_alter_table('game') as batch_op:
        if 'stage_deadline' not in cols:
            batch_op.add_column(sa.Column('stage_deadline', sa.Float(), nullable=True))
        if 'round_history' not in cols:
            batch_op.add_column(sa.Column('round_history', sa.Text(), nullable=True))


def downgrade():
    with op.batch_alter_table('game') as batch_op:
        batch_op.drop_column('round_history')
        batch_op.drop_column('stage_deadline')


