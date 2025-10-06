"""Ajustar tags para funcionar many-to-many

Revision ID: 47ad127f21f8
Revises: 18d9478610e0
Create Date: 2025-10-02 23:54:02.620326

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '47ad127f21f8'
down_revision: Union[str, Sequence[str], None] = '18d9478610e0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Criar nova tabela de associação
    op.create_table(
        'manga_tags',
        sa.Column('manga_id', sa.Integer(), sa.ForeignKey('mangas.id', ondelete="CASCADE"), primary_key=True),
        sa.Column('tag_id', sa.Integer(), sa.ForeignKey('tags.id', ondelete="CASCADE"), primary_key=True)
    )
    
     # Remover a coluna antiga que ligava diretamente tags → mangas
    with op.batch_alter_table('tags') as batch_op:
        batch_op.drop_column('manga_id')
        batch_op.create_unique_constraint("uq_tags_nome", ["tag"])  # garante tags únicas
    pass


def downgrade() -> None:
    # Recriar a coluna manga_id na tabela tags
    with op.batch_alter_table('tags') as batch_op:
        batch_op.add_column(sa.Column('manga_id', sa.Integer(), sa.ForeignKey('mangas.id')))
        batch_op.drop_constraint("uq_tags_nome", type_="unique")

    # Dropar tabela associativa
    op.drop_table('manga_tags')
    pass
