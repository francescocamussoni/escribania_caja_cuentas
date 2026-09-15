"""Add fecha_override column to movimiento and update composite index.

Adds nullable TIMESTAMPTZ column `fecha_override` to `movimiento`.
When present, this column holds an explicit business date for the movement
(set to 09:00 AM Argentina time by the application layer).
When NULL, the movement's display date falls back to `created_at`.

The composite index used for per-currency subtotal lookups is replaced
by an expression index that uses COALESCE(fecha_override, created_at)
so that ordering respects the explicit date when provided.

Revision ID: 009_movimiento_fecha_override
Revises: 008_movimiento_moneda
Create Date: 2026-09-14
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "009_movimiento_fecha_override"
down_revision: Union[str, None] = "008_movimiento_moneda"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Add nullable fecha_override column.
    op.add_column(
        "movimiento",
        sa.Column(
            "fecha_override",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
    )

    # 2. Drop the old index that ordered only by created_at.
    op.drop_index("idx_movimiento_caja_moneda_created", table_name="movimiento")

    # 3. Create expression index using COALESCE(fecha_override, created_at).
    #    This ensures that movements with an explicit fecha_override are ordered
    #    by that date, while movements without it fall back to created_at.
    #    op.create_index does not support COALESCE expressions directly, so we
    #    use op.execute with raw DDL.
    op.execute(
        """
        CREATE INDEX idx_movimiento_caja_moneda_fecha
        ON movimiento (
            caja_id,
            moneda,
            COALESCE(fecha_override, created_at) DESC,
            id DESC
        )
        """
    )


def downgrade() -> None:
    # 1. Drop the COALESCE expression index.
    op.drop_index("idx_movimiento_caja_moneda_fecha", table_name="movimiento")

    # 2. Recreate the original created_at-based composite index.
    op.create_index(
        "idx_movimiento_caja_moneda_created",
        "movimiento",
        ["caja_id", "moneda", sa.text("created_at DESC"), sa.text("id DESC")],
    )

    # 3. Drop the fecha_override column.
    op.drop_column("movimiento", "fecha_override")
