"""Add cheque/echeque support to movimiento.

Adds to `movimiento`:
  - `instrumento`        VARCHAR(10) NOT NULL  ('ninguno' | 'cheque' | 'echeque')
  - `fecha_liquidacion`  DATE NULL             (estimated settlement date)
  - `fecha_liquidado`    TIMESTAMPTZ NULL      (when the cheque was settled; NULL = pending)

`subtotal` becomes NULLABLE: pending cheques do not impact the balance, so they have
no subtotal. Three CHECK constraints keep the data coherent at database level.

The per-currency stream index is replaced by a partial index over rows that impact the
balance (`subtotal IS NOT NULL`) using the effective date
COALESCE(fecha_liquidado, fecha_override, created_at). Two partial indexes support
pending cheque lookups.

Existing rows become `instrumento = 'ninguno'` and keep their subtotal untouched.

Downgrade refuses to run while pending cheques exist (they cannot be represented
without the new columns); liquidated cheques are kept as common movements.

Revision ID: 010_movimiento_cheque
Revises: 009_movimiento_fecha_override
Create Date: 2026-10-21
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "010_movimiento_cheque"
down_revision: Union[str, None] = "009_movimiento_fecha_override"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. New columns. `instrumento` is added with a server default so existing rows are
    #    backfilled with 'ninguno', then the default is dropped (the ORM sets it).
    op.add_column(
        "movimiento",
        sa.Column(
            "instrumento",
            sa.String(length=10),
            nullable=False,
            server_default="ninguno",
        ),
    )
    op.alter_column("movimiento", "instrumento", server_default=None)
    op.add_column("movimiento", sa.Column("fecha_liquidacion", sa.Date(), nullable=True))
    op.add_column(
        "movimiento",
        sa.Column("fecha_liquidado", sa.DateTime(timezone=True), nullable=True),
    )

    # 2. Pending cheques have no subtotal.
    op.alter_column("movimiento", "subtotal", existing_type=sa.Numeric(15, 2), nullable=True)

    # 3. Integrity constraints.
    op.create_check_constraint(
        "ck_movimiento_instrumento",
        "movimiento",
        "instrumento IN ('ninguno', 'cheque', 'echeque')",
    )
    op.create_check_constraint(
        "ck_movimiento_cheque_fechas",
        "movimiento",
        "(instrumento = 'ninguno' AND fecha_liquidacion IS NULL AND fecha_liquidado IS NULL) "
        "OR (instrumento <> 'ninguno' AND fecha_liquidacion IS NOT NULL)",
    )
    op.create_check_constraint(
        "ck_movimiento_subtotal_estado",
        "movimiento",
        "(subtotal IS NOT NULL) = (instrumento = 'ninguno' OR fecha_liquidado IS NOT NULL)",
    )

    # 4. Replace the stream index with a partial one over the effective date.
    op.drop_index("idx_movimiento_caja_moneda_fecha", table_name="movimiento")
    op.execute(
        """
        CREATE INDEX idx_movimiento_stream_efectiva
        ON movimiento (
            caja_id,
            moneda,
            COALESCE(fecha_liquidado, fecha_override, created_at) DESC,
            id DESC
        )
        WHERE subtotal IS NOT NULL
        """
    )

    # 5. Partial indexes for pending cheques.
    op.execute(
        """
        CREATE INDEX idx_movimiento_cheque_pendiente
        ON movimiento (fecha_liquidacion, id)
        WHERE instrumento <> 'ninguno' AND fecha_liquidado IS NULL
        """
    )
    op.execute(
        """
        CREATE INDEX idx_movimiento_cheque_caja_pendiente
        ON movimiento (caja_id, moneda, fecha_liquidacion, id)
        WHERE instrumento <> 'ninguno' AND fecha_liquidado IS NULL
        """
    )


def downgrade() -> None:
    bind = op.get_bind()
    pending = bind.execute(
        sa.text(
            "SELECT COUNT(*) FROM movimiento "
            "WHERE instrumento <> 'ninguno' AND fecha_liquidado IS NULL"
        )
    ).scalar_one()
    if pending:
        raise RuntimeError(
            f"No se puede revertir 010_movimiento_cheque: existen {pending} cheque(s) "
            "pendiente(s). Liquídelos o elimínelos antes de hacer el downgrade."
        )

    op.drop_index("idx_movimiento_cheque_caja_pendiente", table_name="movimiento")
    op.drop_index("idx_movimiento_cheque_pendiente", table_name="movimiento")
    op.drop_index("idx_movimiento_stream_efectiva", table_name="movimiento")

    op.drop_constraint("ck_movimiento_subtotal_estado", "movimiento", type_="check")
    op.drop_constraint("ck_movimiento_cheque_fechas", "movimiento", type_="check")
    op.drop_constraint("ck_movimiento_instrumento", "movimiento", type_="check")

    # Every remaining row has a subtotal (common movements and liquidated cheques).
    op.alter_column("movimiento", "subtotal", existing_type=sa.Numeric(15, 2), nullable=False)

    op.drop_column("movimiento", "fecha_liquidado")
    op.drop_column("movimiento", "fecha_liquidacion")
    op.drop_column("movimiento", "instrumento")

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
