"""merge multiple heads

Revision ID: merge_20250827
Revises: aaddaf18b59a, e3f1b2c34add, 8f1b2c3a4d5e
Create Date: 2025-08-27 15:10:00
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'merge_20250827'
down_revision = ('e3f1b2c34add',)
branch_labels = None
depends_on = None


def upgrade():
    pass


def downgrade():
    pass


