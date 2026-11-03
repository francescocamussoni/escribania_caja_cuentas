"""Sección "Cheques": cheques pendientes de todas las cajas (feature 010, US3)."""

from math import ceil
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.dates import end_of_month, today_ar
from app.db.session import get_db
from app.models.movimiento import Movimiento
from app.models.usuario import Usuario
from app.schemas.movimiento import PaginatedMovimientosResponse, movimiento_to_response
from app.services.cheque_service import PAGE_SIZE, list_cheques_pendientes_page

router = APIRouter()


@router.get("", response_model=PaginatedMovimientosResponse)
def list_cheques(
    current_user: Annotated[Usuario, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
    categoria: Annotated[Literal["aptos", "proximos"], Query()],
    page: Annotated[int, Query(ge=1)] = 1,
) -> PaginatedMovimientosResponse:
    """Pending cheques of every caja, split in two categories relative to "today" (AR).

    - `aptos`: fecha de liquidación is today or earlier (ready to be settled).
    - `proximos`: after today and up to the end of the current month.

    Readable by any authenticated role; `liquidable` is only true for the Secretaria.
    """
    hoy = today_ar()
    if categoria == "aptos":
        where = Movimiento.fecha_liquidacion <= hoy
    else:
        where = (Movimiento.fecha_liquidacion > hoy) & (
            Movimiento.fecha_liquidacion <= end_of_month(hoy)
        )

    items, total_items = list_cheques_pendientes_page(db, where=where, page=page)
    return PaginatedMovimientosResponse(
        items=[movimiento_to_response(item, current_user) for item in items],
        page=page,
        page_size=PAGE_SIZE,
        total_items=total_items,
        total_pages=ceil(total_items / PAGE_SIZE) if total_items else 0,
    )
