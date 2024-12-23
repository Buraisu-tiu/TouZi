"""add asset

Revision ID: 6a009a8db292
Revises: 43671078b66d
Create Date: 2024-12-23 09:44:59.071861

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '6a009a8db292'
down_revision = '43671078b66d'
branch_labels = None
depends_on = None


def upgrade():
    # Add the new column with a default value for existing rows
    op.add_column('portfolios', sa.Column('asset_type', sa.String(length=10), nullable=False, server_default='stock'))
    # Remove the server default after updating existing rows
    op.alter_column('portfolios', 'asset_type', server_default=None)

def downgrade():
    # Remove the column if downgrading
    op.drop_column('portfolios', 'asset_type')


    # ### end Alembic commands ###
