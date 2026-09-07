"""Add moneda column to movimiento.

Adds VARCHAR(3) NOT NULL DEFAULT 'ARS' with CHECK IN ('ARS','USD').
Backfills existing rows to 'ARS'. Creates composite index
(caja_id, moneda, created_at DESC, id DESC) for per-currency subtotal queries.

Revision ID: 008_movimiento_moneda
Revises: 007_evento_desarchivar
Create Date: 2026-09-07
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "008_movimiento_moneda"
down_revision: Union[str, None] = "007_evento_desarchivar"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Add column with server-side default so existing rows get 'ARS' immediately.
    op.add_column(
        "movimiento",
        sa.Column(
            "moneda",
            sa.String(3),
            nullable=False,
            server_default="ARS",
        ),
    )

    # 2. CHECK constraint: only 'ARS' or 'USD' allowed.
    op.create_check_constraint(
        "ck_movimiento_moneda",
        "movimiento",
        "moneda IN ('ARS', 'USD')",
    )

    # 3. Drop the server-side default so application code controls the value
    #    (Alembic / SQLAlchemy will set it from the ORM default going forward).
    op.alter_column("movimiento", "moneda", server_default=None)

    # 4. Composite index for per-currency subtotal lookups:
    #    ORDER BY created_at DESC, id DESC  (latest row in stream)
    op.create_index(
        "idx_movimiento_caja_moneda_created",
        "movimiento",
        ["caja_id", "moneda", sa.text("created_at DESC"), sa.text("id DESC")],
    )


def downgrade() -> None:
    op.drop_index("idx_movimiento_caja_moneda_created", table_name="movimiento")
    op.drop_constraint("ck_movimiento_moneda", "movimiento", type_="check")
    op.drop_column("movimiento", "moneda")
