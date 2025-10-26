"""Проверка наличия изменени

Revision ID: 03a90d4c4b00
Revises: 1f8b6cdacee3
Create Date: 2025-10-26 14:18:47.201180

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '03a90d4c4b00'
down_revision: Union[str, Sequence[str], None] = '1f8b6cdacee3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
