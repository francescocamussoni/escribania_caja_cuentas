from datetime import date
from decimal import Decimal
from math import ceil
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import Date, cast, func, select
from sqlalchemy.orm import Session, selectinload
from zoneinfo import ZoneInfo

from app.api.deps import get_current_user, require_role
from app.core.logging import get_logger, log_security_event
from app.db.session import get_db
from app.models.caja import Caja
from app.models.movimiento import Movimiento
from app.models.usuario import Usuario
from app.schemas.movimiento import (
    CreateMovimientoRequest,
    MovimientoCreateResponse,
    MovimientoResponse,
    PaginatedMovimientosResponse,
    UpdateMovimientoRequest,
    movimiento_to_response,
)
from app.services.movimiento_service import MovimientoNotFoundError, MovimientoService

router = APIRouter()
PAGE_SIZE = 20
logger = get_logger(__name__)

_ARGENTINA_TZ = ZoneInfo("America/Argentina/Buenos_Aires")


@router.get("/{caja_id}/movimientos", response_model=PaginatedMovimientosResponse)
def list_movimientos(
    caja_id: int,
    current_user: Annotated[Usuario, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query()] = PAGE_SIZE,
    moneda: Annotated[str | None, Query(pattern="^(ARS|USD)$")] = None,
    fecha_desde: Annotated[date | None, Query()] = None,
    fecha_hasta: Annotated[date | None, Query()] = None,
) -> PaginatedMovimientosResponse:
    if page_size != PAGE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="page_size debe ser 20",
        )

    # T030 — validar rango de fechas
    if fecha_desde is not None and fecha_hasta is not None and fecha_desde > fecha_hasta:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="fecha_desde no puede ser posterior a fecha_hasta",
        )

    caja = db.get(Caja, caja_id)
    if caja is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Caja no encontrada")

    # Construir filtros base
    base_filter = Movimiento.caja_id == caja_id
    if moneda is not None:
        base_filter = base_filter & (Movimiento.moneda == moneda)

    # Filtro de fecha en TZ Argentina: cast created_at a Date local
    if fecha_desde is not None:
        base_filter = base_filter & (
            cast(Movimiento.created_at.op("AT TIME ZONE")("America/Argentina/Buenos_Aires"), Date)
            >= fecha_desde
        )
    if fecha_hasta is not None:
        base_filter = base_filter & (
            cast(Movimiento.created_at.op("AT TIME ZONE")("America/Argentina/Buenos_Aires"), Date)
            <= fecha_hasta
        )

    total_items = db.scalar(
        select(func.count())
        .select_from(Movimiento)
        .where(base_filter)
    )
    total_items = total_items or 0
    total_pages = ceil(total_items / PAGE_SIZE) if total_items else 0

    movimientos = db.scalars(
        select(Movimiento)
        .where(base_filter)
        .options(selectinload(Movimiento.caja))
        .order_by(Movimiento.created_at.desc(), Movimiento.id.desc())
        .offset((page - 1) * PAGE_SIZE)
        .limit(PAGE_SIZE)
    ).all()

    return PaginatedMovimientosResponse(
        items=[movimiento_to_response(movimiento, current_user) for movimiento in movimientos],
        page=page,
        page_size=PAGE_SIZE,
        total_items=total_items,
        total_pages=total_pages,
    )


@router.post(
    "/{caja_id}/movimientos",
    response_model=MovimientoCreateResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_movimiento(
    caja_id: int,
    payload: CreateMovimientoRequest,
    current_user: Annotated[Usuario, Depends(require_role("secretaria"))],
    db: Annotated[Session, Depends(get_db)],
) -> MovimientoCreateResponse:
    caja = db.get(Caja, caja_id)
    if caja is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Caja no encontrada")

    service = MovimientoService(db)

    if payload.registrar_complementario:
        try:
            movimiento, complementario_mov = service.create_movimiento_pair(
                caja_id=caja_id,
                descripcion=payload.descripcion,
                monto=Decimal(payload.monto),
                tipo=payload.tipo,
                user=current_user,
            )
        except Exception:
            db.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="No se pudo registrar el par de movimientos.",
            ) from None
        db.commit()
        db.refresh(movimiento)
        db.refresh(complementario_mov)
        movimiento.caja = caja
        complementario_mov.caja = caja
        log_security_event(
            logger,
            "movimiento_created",
            username=current_user.username,
            rol=current_user.rol,
            caja_id=caja_id,
            movimiento_id=movimiento.id,
            tipo=movimiento.tipo,
            moneda=movimiento.moneda,
            complementario_id=complementario_mov.id,
        )
        return MovimientoCreateResponse(
            movimiento=movimiento_to_response(movimiento, current_user),
            complementario=movimiento_to_response(complementario_mov, current_user),
        )

    movimiento = service.create_movimiento(
        caja_id=caja_id,
        descripcion=payload.descripcion,
        monto=Decimal(payload.monto),
        tipo=payload.tipo,
        moneda=payload.moneda,
        user=current_user,
    )
    db.commit()
    db.refresh(movimiento)
    movimiento.caja = caja
    log_security_event(
        logger,
        "movimiento_created",
        username=current_user.username,
        rol=current_user.rol,
        caja_id=caja_id,
        movimiento_id=movimiento.id,
        tipo=movimiento.tipo,
        moneda=movimiento.moneda,
    )
    return MovimientoCreateResponse(
        movimiento=movimiento_to_response(movimiento, current_user),
        complementario=None,
    )


@router.patch(
    "/{caja_id}/movimientos/{movimiento_id}",
    response_model=MovimientoResponse,
)
def update_movimiento(
    caja_id: int,
    movimiento_id: int,
    payload: UpdateMovimientoRequest,
    current_user: Annotated[Usuario, Depends(require_role("secretaria"))],
    db: Annotated[Session, Depends(get_db)],
) -> MovimientoResponse:
    caja = db.get(Caja, caja_id)
    if caja is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Caja no encontrada")

    service = MovimientoService(db)
    try:
        movimiento = service.update_movimiento(
            caja_id=caja_id,
            movimiento_id=movimiento_id,
            user=current_user,
            descripcion=payload.descripcion,
            monto=Decimal(payload.monto) if payload.monto is not None else None,
            tipo=payload.tipo,
            moneda=payload.moneda,
        )
    except MovimientoNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Movimiento no encontrado",
        ) from None
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc

    db.commit()
    db.refresh(movimiento)
    movimiento.caja = caja
    log_security_event(
        logger,
        "movimiento_updated",
        username=current_user.username,
        rol=current_user.rol,
        caja_id=caja_id,
        movimiento_id=movimiento.id,
        tipo=movimiento.tipo,
    )
    return movimiento_to_response(movimiento, current_user)


@router.delete(
    "/{caja_id}/movimientos/{movimiento_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_movimiento(
    caja_id: int,
    movimiento_id: int,
    current_user: Annotated[Usuario, Depends(require_role("secretaria"))],
    db: Annotated[Session, Depends(get_db)],
) -> None:
    caja = db.get(Caja, caja_id)
    if caja is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Caja no encontrada")

    service = MovimientoService(db)
    try:
        service.delete_movimiento(
            caja_id=caja_id,
            movimiento_id=movimiento_id,
            user=current_user,
        )
    except MovimientoNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Movimiento no encontrado",
        ) from None

    db.commit()
    log_security_event(
        logger,
        "movimiento_deleted",
        username=current_user.username,
        rol=current_user.rol,
        caja_id=caja_id,
        movimiento_id=movimiento_id,
    )
