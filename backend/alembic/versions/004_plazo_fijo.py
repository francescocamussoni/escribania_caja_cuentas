"""Create plazo_fijo table.

Revision ID: 004_plazo_fijo
Revises: 003_movimiento_updated_by
Create Date: 2026-08-06
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "004_plazo_fijo"
down_revision: Union[str, None] = "003_movimiento_updated_by"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "plazo_fijo",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("caja_id", sa.SmallInteger(), nullable=False),
        sa.Column("monto_ingresado", sa.Numeric(15, 2), nullable=False),
        sa.Column("monto_a_vencimiento", sa.Numeric(15, 2), nullable=False),
        sa.Column("fecha_vencimiento", sa.Date(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("created_by", sa.Integer(), nullable=False),
        sa.CheckConstraint(
            "monto_ingresado > 0",
            name="ck_plazo_fijo_monto_ingresado_positive",
        ),
        sa.CheckConstraint(
            "monto_a_vencimiento > 0",
            name="ck_plazo_fijo_monto_a_vencimiento_positive",
        ),
        sa.CheckConstraint(
            "monto_a_vencimiento >= monto_ingresado",
            name="ck_plazo_fijo_montos_order",
        ),
        sa.ForeignKeyConstraint(["caja_id"], ["caja.id"]),
        sa.ForeignKeyConstraint(["created_by"], ["usuario.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_index(
        "idx_plazo_fijo_caja_vencimiento",
        "plazo_fijo",
        [
            "caja_id",
            "fecha_vencimiento",
            sa.text("created_at DESC"),
            sa.text("id DESC"),
        ],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("idx_plazo_fijo_caja_vencimiento", table_name="plazo_fijo")
    op.drop_table("plazo_fijo")
