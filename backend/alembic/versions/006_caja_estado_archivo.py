"""Add caja archive state and configuration audit events.

Revision ID: 006_caja_estado_archivo
Revises: 005_usuario_password_changed_at
Create Date: 2026-08-14
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "006_caja_estado_archivo"
down_revision: Union[str, None] = "005_usuario_password_changed_at"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column(
        "caja",
        "nombre",
        existing_type=sa.String(length=100),
        type_=sa.String(length=120),
        existing_nullable=False,
    )
    op.alter_column(
        "caja",
        "slug",
        existing_type=sa.String(length=100),
        type_=sa.String(length=120),
        existing_nullable=False,
    )
    op.add_column(
        "caja",
        sa.Column(
            "estado",
            sa.String(length=20),
            nullable=False,
            server_default="activa",
        ),
    )
    op.add_column(
        "caja",
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )
    op.add_column(
        "caja",
        sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "caja",
        sa.Column("archived_by_user_id", sa.Integer(), nullable=True),
    )
    op.create_foreign_key(
        "fk_caja_archived_by_user_id",
        "caja",
        "usuario",
        ["archived_by_user_id"],
        ["id"],
    )
    op.create_check_constraint(
        "ck_caja_estado",
        "caja",
        "estado IN ('activa', 'archivada')",
    )

    op.create_table(
        "evento_configuracion_caja",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("caja_id", sa.SmallInteger(), nullable=True),
        sa.Column("accion", sa.String(length=20), nullable=False),
        sa.Column("resultado", sa.String(length=20), nullable=False),
        sa.Column("actor_user_id", sa.Integer(), nullable=False),
        sa.Column("detalle", sa.String(length=500), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "accion IN ('crear', 'archivar')",
            name="ck_evento_configuracion_caja_accion",
        ),
        sa.CheckConstraint(
            "resultado IN ('exito', 'rechazo', 'error')",
            name="ck_evento_configuracion_caja_resultado",
        ),
        sa.ForeignKeyConstraint(["caja_id"], ["caja.id"]),
        sa.ForeignKeyConstraint(["actor_user_id"], ["usuario.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "idx_evento_configuracion_caja_caja_created",
        "evento_configuracion_caja",
        ["caja_id", sa.text("created_at DESC")],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "idx_evento_configuracion_caja_caja_created",
        table_name="evento_configuracion_caja",
    )
    op.drop_table("evento_configuracion_caja")
    op.drop_constraint("ck_caja_estado", "caja", type_="check")
    op.drop_constraint("fk_caja_archived_by_user_id", "caja", type_="foreignkey")
    op.drop_column("caja", "archived_by_user_id")
    op.drop_column("caja", "archived_at")
    op.drop_column("caja", "updated_at")
    op.drop_column("caja", "estado")
    op.alter_column(
        "caja",
        "slug",
        existing_type=sa.String(length=120),
        type_=sa.String(length=100),
        existing_nullable=False,
    )
    op.alter_column(
        "caja",
        "nombre",
        existing_type=sa.String(length=120),
        type_=sa.String(length=100),
        existing_nullable=False,
    )
