"""Add usuario.password_changed_at for JWT session cutover.

Revision ID: 005_usuario_password_changed_at
Revises: 004_plazo_fijo
Create Date: 2026-08-14
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "005_usuario_password_changed_at"
down_revision: Union[str, None] = "004_plazo_fijo"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "usuario",
        sa.Column("password_changed_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("usuario", "password_changed_at")
