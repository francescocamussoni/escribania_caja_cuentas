"""Create caja and movimiento tables.

Revision ID: 002_create_caja_movimiento
Revises: 001_create_usuario
Create Date: 2026-08-03
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "002_create_caja_movimiento"
down_revision: Union[str, None] = "001_create_usuario"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "caja",
        sa.Column("id", sa.SmallInteger(), autoincrement=True, nullable=False),
        sa.Column("nombre", sa.String(length=100), nullable=False),
        sa.Column("slug", sa.String(length=100), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("nombre"),
        sa.UniqueConstraint("slug"),
    )

    op.create_table(
        "movimiento",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("caja_id", sa.SmallInteger(), nullable=False),
        sa.Column("descripcion", sa.String(length=500), nullable=False),
        sa.Column("monto", sa.Numeric(15, 2), nullable=False),
        sa.Column("tipo", sa.String(length=10), nullable=False),
        sa.Column("subtotal", sa.Numeric(15, 2), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("created_by", sa.Integer(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_by", sa.Integer(), nullable=True),
        sa.CheckConstraint("monto > 0", name="ck_movimiento_monto_positive"),
        sa.CheckConstraint(
            "tipo IN ('entrada', 'salida')",
            name="ck_movimiento_tipo",
        ),
        sa.ForeignKeyConstraint(["caja_id"], ["caja.id"]),
        sa.ForeignKeyConstraint(["created_by"], ["usuario.id"]),
        sa.ForeignKeyConstraint(["updated_by"], ["usuario.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_index(
        "idx_movimiento_caja_created",
        "movimiento",
        ["caja_id", sa.text("created_at DESC"), sa.text("id DESC")],
        unique=False,
    )
    op.create_index(
        "idx_movimiento_caja_id",
        "movimiento",
        ["caja_id", "id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("idx_movimiento_caja_id", table_name="movimiento")
    op.drop_index("idx_movimiento_caja_created", table_name="movimiento")
    op.drop_table("movimiento")
    op.drop_table("caja")
