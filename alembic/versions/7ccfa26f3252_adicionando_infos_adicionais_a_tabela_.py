"""Adicionando infos adicionais a tabela de mangas

Revision ID: 7ccfa26f3252
Revises: afa3f290e645
Create Date: 2025-10-02 10:32:29.875844

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '7ccfa26f3252'
down_revision: Union[str, Sequence[str], None] = 'afa3f290e645'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('mangas', sa.Column('status', sa.String(), nullable=True))
    op.add_column('mangas', sa.Column('thumbnail', sa.String(), nullable=True))
    op.add_column('mangas', sa.Column('avaliacao', sa.Float(), nullable=True))
    pass


def downgrade() -> None:
    op.drop_column('mangas', 'status')
    op.drop_column('mangas', 'thumbnail')
    op.drop_column('mangas', 'avaliacao')
    pass
