"""Criar coluna de baixado no Capitulo

Revision ID: afa3f290e645
Revises: 904eed554e59
Create Date: 2025-09-26 16:52:12.159052

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'afa3f290e645'
down_revision: Union[str, Sequence[str], None] = '904eed554e59'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'capitulos',
        sa.Column('baixado', sa.Boolean(), nullable=False, default=False)
    )
    pass


def downgrade() -> None:
    op.drop_column('capitulos', 'baixado')
    pass
