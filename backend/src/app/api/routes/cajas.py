from typing import Annotated
from decimal import Decimal

from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_role
from app.core.logging import get_logger, log_security_event
from app.db.session import get_db
from app.models.caja import Caja
from app.models.movimiento import Movimiento, effective_date_expr
from app.models.usuario import Usuario
from app.schemas.caja import (
    CajaCreateRequest,
    CajaResponse,
    CajaSaldoGeneralResponse,
    CajaSaldoResumenItem,
    CajaSaldoResponse,
)
from app.core.dates import today_ar
from app.schemas.movimiento import (
    SaldoFuturoDetalle,
    SaldoFuturoFila,
    SaldoFuturoMoneda,
    SaldoFuturoResponse,
    SaldoProyectadoMoneda,
    SaldoProyectadoResponse,
    format_decimal,
)
from app.services.cheque_service import build_saldo_futuro
from app.services.saldo_futuro import saldo_a_fecha
from app.services.saldo_service import get_saldos_caja
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
    total_ars = sum((saldo_ars for _, saldo_ars, _ in rows), Decimal("0.00"))
    total_usd = sum((saldo_usd for _, _, saldo_usd in rows), Decimal("0.00"))
    log_security_event(
        logger,
        "caja_saldo_general_viewed",
        username=current_user.username,
        cajas_incluidas=len(rows),
    )
    return CajaSaldoGeneralResponse(
        subtotal_general_ars=format_decimal(total_ars),
        subtotal_general_usd=format_decimal(total_usd),
        cajas_incluidas=len(rows),
        cajas=[
            CajaSaldoResumenItem(
                caja=CajaResponse.model_validate(caja),
                saldo_ars=format_decimal(saldo_ars),
                saldo_usd=format_decimal(saldo_usd),
            )
            for caja, saldo_ars, saldo_usd in rows
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

    saldo_ars, saldo_usd = get_saldos_caja(db, caja_id)

    # Most recent movement that impacts the balance (by effective date).
    ultimo = db.scalar(
        select(func.max(effective_date_expr())).where(
            Movimiento.caja_id == caja_id,
            Movimiento.subtotal.is_not(None),
        )
    )
    ultimo_movimiento_at: str | None = ultimo.isoformat() if ultimo is not None else None

    return CajaSaldoResponse(
        caja=CajaResponse.model_validate(caja),
        saldo_ars=format_decimal(saldo_ars),
        saldo_usd=format_decimal(saldo_usd),
        ultimo_movimiento_at=ultimo_movimiento_at,
    )


@router.get("/{caja_id}/saldo-futuro", response_model=SaldoFuturoResponse)
def get_caja_saldo_futuro(
    caja_id: int,
    current_user: Annotated[Usuario, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> SaldoFuturoResponse:
    """Saldo de hoy + saldo proyectado acumulado por fecha de liquidación (read-only)."""
    _ = current_user
    caja = db.get(Caja, caja_id)
    if caja is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Caja no encontrada")

    hoy = today_ar()
    proyeccion = build_saldo_futuro(db, caja_id, hoy)
    return SaldoFuturoResponse(
        caja=CajaResponse.model_validate(caja),
        fecha_calculo=hoy,
        monedas=[
            SaldoFuturoMoneda(
                moneda=moneda,  # type: ignore[arg-type]
                saldo_actual=format_decimal(saldo_actual),
                filas=[
                    SaldoFuturoFila(
                        fecha_liquidacion=fila.fecha_liquidacion,
                        vencido=fila.vencido,
                        cheques=fila.cheques,
                        efecto_neto=format_decimal(fila.efecto_neto),
                        saldo_proyectado=format_decimal(fila.saldo_proyectado),
                        detalle=[
                            SaldoFuturoDetalle(
                                descripcion=item.descripcion,
                                instrumento=item.instrumento,  # type: ignore[arg-type]
                                tipo=item.tipo,  # type: ignore[arg-type]
                                monto=format_decimal(item.monto),
                            )
                            for item in fila.detalle
                        ],
                    )
                    for fila in filas
                ],
            )
            for moneda, (saldo_actual, filas) in proyeccion.items()
        ],
    )


@router.get("/{caja_id}/saldo-proyectado", response_model=SaldoProyectadoResponse)
def get_caja_saldo_proyectado(
    caja_id: int,
    current_user: Annotated[Usuario, Depends(require_role("secretaria"))],
    db: Annotated[Session, Depends(get_db)],
    fecha: Annotated[
        date | None,
        Query(description="Fecha futura (YYYY-MM-DD). Sin fecha: todos los cheques pendientes"),
    ] = None,
) -> SaldoProyectadoResponse:
    """Valor de caja total on a future date: today's balance +- pending cheques due by then.

    Secretaria only. The server does all the math (same projection as saldo-futuro).
    """
    _ = current_user
    caja = db.get(Caja, caja_id)
    if caja is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Caja no encontrada")

    hoy = today_ar()
    if fecha is not None and fecha <= hoy:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="La fecha debe ser posterior a hoy",
        )

    proyeccion = build_saldo_futuro(db, caja_id, hoy)
    monedas = []
    for moneda, (saldo_actual, filas) in proyeccion.items():
        efecto, saldo, cheques = saldo_a_fecha(
            saldo_actual, filas, fecha if fecha is not None else date.max
        )
        monedas.append(
            SaldoProyectadoMoneda(
                moneda=moneda,  # type: ignore[arg-type]
                saldo_actual=format_decimal(saldo_actual),
                efecto_cheques=format_decimal(efecto),
                saldo_proyectado=format_decimal(saldo),
                cheques=cheques,
            )
        )
    return SaldoProyectadoResponse(
        caja=CajaResponse.model_validate(caja), fecha=fecha, monedas=monedas
    )
