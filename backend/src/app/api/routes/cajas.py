from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.caja import Caja
from app.models.movimiento import Movimiento
from app.models.usuario import Usuario
from app.schemas.caja import CajaResponse, CajaSaldoResponse
from app.schemas.movimiento import format_decimal

router = APIRouter()

PAGE_SIZE = 20


@router.get("", response_model=list[CajaResponse])
def list_cajas(
    current_user: Annotated[Usuario, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> list[Caja]:
    _ = current_user
    return list(db.scalars(select(Caja).order_by(Caja.id)).all())


@router.get("/{caja_id}/saldo", response_model=CajaSaldoResponse)
def get_caja_saldo(
    caja_id: int,
    current_user: Annotated[Usuario, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> CajaSaldoResponse:
    _ = current_user
    caja = db.get(Caja, caja_id)
    if caja is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Caja no encontrada")

    last_movimiento = db.scalar(
        select(Movimiento)
        .where(Movimiento.caja_id == caja_id)
        .order_by(Movimiento.created_at.desc(), Movimiento.id.desc())
    )
    saldo_actual = format_decimal(last_movimiento.subtotal) if last_movimiento else "0.00"
    ultimo_movimiento_at = (
        last_movimiento.created_at.isoformat() if last_movimiento else None
    )

    return CajaSaldoResponse(
        caja=CajaResponse.model_validate(caja),
        saldo_actual=saldo_actual,
        ultimo_movimiento_at=ultimo_movimiento_at,
    )
