"""Alterando tabela de manga e adicionando tags

Revision ID: 18d9478610e0
Revises: 7ccfa26f3252
Create Date: 2025-10-02 13:40:58.175137

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '18d9478610e0'
down_revision: Union[str, Sequence[str], None] = '7ccfa26f3252'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('mangas', sa.Column('avalicao', sa.Float(), nullable=True))
    op.create_table('tags',
                    sa.Column('id', sa.Integer(), nullable=False),
                    sa.Column('manga_id', sa.Integer(), nullable=False),
                    sa.Column('tag', sa.String(), nullable=False),
                    sa.ForeignKeyConstraint(['manga_id'], ['mangas.id'], ),
                    sa.PrimaryKeyConstraint('id')
    )
    pass


def downgrade() -> None:
    op.drop_table('tags')
    op.alter_column('mangas', 'avalicao', type_=sa.String(), nullable=True)
    pass
