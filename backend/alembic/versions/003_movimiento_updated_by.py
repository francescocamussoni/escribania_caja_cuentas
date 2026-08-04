"""Document movimiento audit columns for amend RFC.

Revision ID: 003_movimiento_updated_by
Revises: 002_create_caja_movimiento
Create Date: 2026-08-03

The updated_at and updated_by columns were introduced in 002_create_caja_movimiento.
This revision exists to align migration history with the amend RFC (edición 24h).
"""

from typing import Sequence, Union

revision: str = "003_movimiento_updated_by"
down_revision: Union[str, None] = "002_create_caja_movimiento"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
