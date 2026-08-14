from typing import Annotated
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_role
from app.core.logging import get_logger, log_security_event
from app.db.session import get_db
from app.models.caja import Caja
from app.models.movimiento import Movimiento
from app.models.usuario import Usuario
from app.schemas.caja import (
    CajaCreateRequest,
    CajaResponse,
    CajaSaldoGeneralResponse,
    CajaSaldoResumenItem,
    CajaSaldoResponse,
)
from app.schemas.movimiento import format_decimal
from app.services.caja_service import (
    CajaDuplicateError,
    CajaNotFoundError,
    archive_caja,
    create_caja,
    list_cajas_activas,
    list_cajas_config,
    list_saldos_cajas_activas,
    unarchive_caja,
)

router = APIRouter()
logger = get_logger(__name__)

PAGE_SIZE = 20


@router.get("", response_model=list[CajaResponse])
def list_cajas(
    current_user: Annotated[Usuario, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> list[Caja]:
    _ = current_user
    return list_cajas_activas(db)


@router.get("/operativas", response_model=list[CajaResponse])
def list_cajas_operativas(
    current_user: Annotated[Usuario, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> list[Caja]:
    _ = current_user
    return list_cajas_activas(db)


@router.get("/saldo-general", response_model=CajaSaldoGeneralResponse)
def get_cajas_saldo_general(
    current_user: Annotated[Usuario, Depends(require_role("secretaria"))],
    db: Annotated[Session, Depends(get_db)],
) -> CajaSaldoGeneralResponse:
    rows = list_saldos_cajas_activas(db)
    total = sum((saldo for _, saldo in rows), Decimal("0.00"))
    log_security_event(
        logger,
        "caja_saldo_general_viewed",
        username=current_user.username,
        cajas_incluidas=len(rows),
    )
    return CajaSaldoGeneralResponse(
        subtotal_general=format_decimal(total),
        cajas_incluidas=len(rows),
        cajas=[
            CajaSaldoResumenItem(
                caja=CajaResponse.model_validate(caja),
                saldo_actual=format_decimal(saldo),
            )
            for caja, saldo in rows
        ],
    )


@router.get("/config", response_model=list[CajaResponse])
def get_cajas_config(
    current_user: Annotated[Usuario, Depends(require_role("secretaria"))],
    db: Annotated[Session, Depends(get_db)],
) -> list[Caja]:
    _ = current_user
    return list_cajas_config(db)


@router.post(
    "/config",
    response_model=CajaResponse,
    status_code=status.HTTP_201_CREATED,
)
def post_cajas_config(
    payload: CajaCreateRequest,
    current_user: Annotated[Usuario, Depends(require_role("secretaria"))],
    db: Annotated[Session, Depends(get_db)],
) -> Caja:
    try:
        caja = create_caja(db, nombre=payload.nombre, actor=current_user)
        db.commit()
        db.refresh(caja)
        return caja
    except CajaDuplicateError as exc:
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    except ValueError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


@router.post("/{caja_id}/archive", response_model=CajaResponse)
def post_caja_archive(
    caja_id: int,
    current_user: Annotated[Usuario, Depends(require_role("secretaria"))],
    db: Annotated[Session, Depends(get_db)],
) -> Caja:
    try:
        caja = archive_caja(db, caja_id=caja_id, actor=current_user)
        db.commit()
        db.refresh(caja)
        return caja
    except CajaNotFoundError as exc:
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc


@router.post("/{caja_id}/unarchive", response_model=CajaResponse)
def post_caja_unarchive(
    caja_id: int,
    current_user: Annotated[Usuario, Depends(require_role("secretaria"))],
    db: Annotated[Session, Depends(get_db)],
) -> Caja:
    try:
        caja = unarchive_caja(db, caja_id=caja_id, actor=current_user)
        db.commit()
        db.refresh(caja)
        return caja
    except CajaNotFoundError as exc:
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc


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
