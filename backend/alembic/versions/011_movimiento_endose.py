"""Add cheque endorsement (endose) links to movimiento.

Adds to `movimiento`:
  - `endosado_a_caja_id`  SMALLINT NULL FK caja.id       (on the CHEQUE: destination caja)
  - `endose_cheque_id`    BIGINT   NULL FK movimiento.id (on the DESTINATION movement:
                                                          cheque that originated it)

Two CHECK constraints keep the data coherent at database level and a partial unique index
guarantees that a cheque originates at most one endorsement movement.

Existing rows keep both columns NULL (no backfill, no behaviour change).

Downgrade refuses to run while endorsements exist.

Revision ID: 011_movimiento_endose
Revises: 010_movimiento_cheque
Create Date: 2026-11-04
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "011_movimiento_endose"
down_revision: Union[str, None] = "010_movimiento_cheque"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "movimiento",
        sa.Column("endosado_a_caja_id", sa.SmallInteger(), nullable=True),
    )
    op.add_column(
        "movimiento",
        sa.Column("endose_cheque_id", sa.BigInteger(), nullable=True),
    )
    op.create_foreign_key(
        "fk_movimiento_endosado_a_caja",
        "movimiento",
        "caja",
        ["endosado_a_caja_id"],
        ["id"],
    )
    op.create_foreign_key(
        "fk_movimiento_endose_cheque",
        "movimiento",
        "movimiento",
        ["endose_cheque_id"],
        ["id"],
    )

    op.create_check_constraint(
        "ck_movimiento_endose_cheque",
        "movimiento",
        "endosado_a_caja_id IS NULL "
        "OR (instrumento <> 'ninguno' AND fecha_liquidado IS NOT NULL)",
    )
    op.create_check_constraint(
        "ck_movimiento_endose_destino",
        "movimiento",
        "endose_cheque_id IS NULL "
        "OR (instrumento = 'ninguno' AND endosado_a_caja_id IS NULL)",
    )

    op.execute(
        """
        CREATE UNIQUE INDEX uq_movimiento_endose_cheque
        ON movimiento (endose_cheque_id)
        WHERE endose_cheque_id IS NOT NULL
        """
    )


def downgrade() -> None:
    bind = op.get_bind()
    endorsed = bind.execute(
        sa.text(
            "SELECT COUNT(*) FROM movimiento "
            "WHERE endosado_a_caja_id IS NOT NULL OR endose_cheque_id IS NOT NULL"
        )
    ).scalar_one()
    if endorsed:
        raise RuntimeError(
            f"No se puede revertir 011_movimiento_endose: existen {endorsed} registro(s) "
            "de endose. Elimínelos manualmente antes de hacer el downgrade."
        )

    op.drop_index("uq_movimiento_endose_cheque", table_name="movimiento")
    op.drop_constraint("ck_movimiento_endose_destino", "movimiento", type_="check")
    op.drop_constraint("ck_movimiento_endose_cheque", "movimiento", type_="check")
    op.drop_constraint("fk_movimiento_endose_cheque", "movimiento", type_="foreignkey")
    op.drop_constraint("fk_movimiento_endosado_a_caja", "movimiento", type_="foreignkey")
    op.drop_column("movimiento", "endose_cheque_id")
    op.drop_column("movimiento", "endosado_a_caja_id")
