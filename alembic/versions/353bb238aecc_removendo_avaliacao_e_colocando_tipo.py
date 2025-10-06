"""removendo avaliacao e colocando tipo

Revision ID: 353bb238aecc
Revises: 47ad127f21f8
Create Date: 2025-10-03 00:32:15.553812

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


# revision identifiers, used by Alembic.
revision: str = '353bb238aecc'
down_revision: Union[str, Sequence[str], None] = '47ad127f21f8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = inspect(conn)

    # lista todas as colunas da tabela "mangas"
    columns = [col["name"] for col in inspector.get_columns("mangas")]

    # se existir a coluna escrita errado "avalicao", remove
    if "avalicao" in columns:
        op.drop_column("mangas", "avalicao")

    # adiciona a coluna tipo se ainda não existir
    if "tipo" not in columns:
        op.add_column("mangas", sa.Column("tipo", sa.String(), nullable=True))


def downgrade() -> None:
    conn = op.get_bind()
    inspector = inspect(conn)
    columns = [col["name"] for col in inspector.get_columns("mangas")]

    if "tipo" in columns:
        op.drop_column("mangas", "tipo")

    # recria a coluna antiga (com erro de digitação)
    if "avalicao" not in columns:
        op.add_column("mangas", sa.Column("avalicao", sa.Float(), nullable=True))

