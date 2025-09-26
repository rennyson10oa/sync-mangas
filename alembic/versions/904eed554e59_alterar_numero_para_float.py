"""Alterar numero para Float

Revision ID: 904eed554e59
Revises: 
Create Date: 2025-09-26 15:33:40.080507

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '904eed554e59'
down_revision = None  # ou a revisão anterior
branch_labels = None
depends_on = None


def upgrade() -> None:
    # altera a coluna numero para float
    op.alter_column(
        'capitulos',
        'numero',
        type_=sa.Float(),
        postgresql_using='numero::double precision'
    )
    pass


def downgrade() -> None:
    # volta para integer, se precisar
    op.alter_column(
        'capitulos',
        'numero',
        type_=sa.Integer(),
        postgresql_using='numero::integer'
    )
    pass
