"""add stage_deadline and round_history to game

Revision ID: e3f1b2c34add
Revises: d4d5eabfd23e
Create Date: 2025-08-27 00:00:00
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'e3f1b2c34add'
down_revision = 'd4d5eabfd23e'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('game') as batch_op:
        batch_op.add_column(sa.Column('stage_deadline', sa.Float(), nullable=True))
        batch_op.add_column(sa.Column('round_history', sa.Text(), nullable=True))


def downgrade():
    with op.batch_alter_table('game') as batch_op:
        batch_op.drop_column('round_history')
        batch_op.drop_column('stage_deadline')


