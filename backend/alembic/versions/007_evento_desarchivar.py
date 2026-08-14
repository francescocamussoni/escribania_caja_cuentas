"""Allow desarchivar in configuration audit events.

Revision ID: 007_evento_desarchivar
Revises: 006_caja_estado_archivo
Create Date: 2026-08-14
"""

from typing import Sequence, Union

from alembic import op

revision: str = "007_evento_desarchivar"
down_revision: Union[str, None] = "006_caja_estado_archivo"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_constraint(
        "ck_evento_configuracion_caja_accion",
        "evento_configuracion_caja",
        type_="check",
    )
    op.create_check_constraint(
        "ck_evento_configuracion_caja_accion",
        "evento_configuracion_caja",
        "accion IN ('crear', 'archivar', 'desarchivar')",
    )


def downgrade() -> None:
    op.drop_constraint(
        "ck_evento_configuracion_caja_accion",
        "evento_configuracion_caja",
        type_="check",
    )
    op.create_check_constraint(
        "ck_evento_configuracion_caja_accion",
        "evento_configuracion_caja",
        "accion IN ('crear', 'archivar')",
    )
