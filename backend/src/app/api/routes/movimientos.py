from datetime import date
from decimal import Decimal
from math import ceil
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import Date, case, cast, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload
from zoneinfo import ZoneInfo

from app.api.deps import get_current_user, require_role
from app.core.logging import get_logger, log_security_event
from app.db.session import get_db
from app.models.caja import Caja
from app.models.movimiento import Movimiento, effective_date_expr
from app.models.usuario import Usuario
from app.schemas.movimiento import (
    CreateMovimientoRequest,
    EndosarChequeRequest,
    EndoseResponse,
    MovimientoCreateResponse,
    MovimientoResponse,
    PaginatedMovimientosResponse,
    UpdateMovimientoRequest,
    format_decimal,
    movimiento_to_response,
)
from app.services.saldo_service import get_valores_totales
from app.services.cheque_service import fecha_carga_expr, list_cheques_pendientes_page
from app.services.movimiento_service import (
    CajaDestinoNotFoundError,
    ChequeAunNoLiquidableError,
    ChequeYaLiquidadoError,
    EndoseDestinoInvalidoError,
    MovimientoEndosadoError,
    MovimientoNotFoundError,
    MovimientoService,
)

router = APIRouter()
PAGE_SIZE = 20
logger = get_logger(__name__)

AR_TZ_NAME = "America/Argentina/Buenos_Aires"
_ARGENTINA_TZ = ZoneInfo(AR_TZ_NAME)


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
    incluir_pendientes: Annotated[bool, Query()] = False,
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

    # By default only rows that impact the balance (common movements and settled cheques)
    # are listed. Registro opts in with `incluir_pendientes` to see pending cheques mixed
    # into the list (they carry no subtotal and sort by their fecha de carga).
    base_filter = Movimiento.caja_id == caja_id
    if not incluir_pendientes:
        base_filter = base_filter & Movimiento.subtotal.is_not(None)
    if moneda is not None:
        base_filter = base_filter & (Movimiento.moneda == moneda)

    # Date filters use the effective date, as a calendar date in Argentina time.
    fecha_ar = cast(func.timezone(AR_TZ_NAME, effective_date_expr()), Date)
    if fecha_desde is not None:
        base_filter = base_filter & (fecha_ar >= fecha_desde)
    if fecha_hasta is not None:
        # "Hasta" is the date the money moves: fecha de cobro (fecha_liquidacion) for
        # cheques/echeques, fecha de registro for everything else.
        es_cheque = Movimiento.instrumento.in_(("cheque", "echeque"))
        fecha_cobro = case(
            (es_cheque & Movimiento.fecha_liquidacion.is_not(None), Movimiento.fecha_liquidacion),
            else_=fecha_ar,
        )
        base_filter = base_filter & (fecha_cobro <= fecha_hasta)

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
        .order_by(effective_date_expr().desc(), Movimiento.id.desc())
        .offset((page - 1) * PAGE_SIZE)
        .limit(PAGE_SIZE)
    ).all()

    items = [movimiento_to_response(movimiento, current_user) for movimiento in movimientos]
    if incluir_pendientes and current_user.rol == "secretaria":
        totales = get_valores_totales(db, caja_id, [m.id for m in movimientos])
        for item in items:
            total = totales.get(item.id)
            item.valor_total = None if total is None else format_decimal(total)

    return PaginatedMovimientosResponse(
        items=items,
        page=page,
        page_size=PAGE_SIZE,
        total_items=total_items,
        total_pages=total_pages,
    )


@router.get(
    "/{caja_id}/cheques-pendientes",
    response_model=PaginatedMovimientosResponse,
)
def list_cheques_pendientes(
    caja_id: int,
    current_user: Annotated[Usuario, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
    page: Annotated[int, Query(ge=1)] = 1,
    moneda: Annotated[str | None, Query(pattern="^(ARS|USD)$")] = None,
    fecha_desde: Annotated[date | None, Query()] = None,
    fecha_hasta: Annotated[date | None, Query()] = None,
) -> PaginatedMovimientosResponse:
    """Pending cheques of one caja (block above the historial in Registro and Consulta)."""
    if fecha_desde is not None and fecha_hasta is not None and fecha_desde > fecha_hasta:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="fecha_desde no puede ser posterior a fecha_hasta",
        )

    caja = db.get(Caja, caja_id)
    if caja is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Caja no encontrada")

    where = Movimiento.caja_id == caja_id
    if moneda is not None:
        where = where & (Movimiento.moneda == moneda)
    # Date filters apply to the fecha de carga, as an Argentina calendar date.
    carga_ar = cast(func.timezone(AR_TZ_NAME, fecha_carga_expr()), Date)
    if fecha_desde is not None:
        where = where & (carga_ar >= fecha_desde)
    if fecha_hasta is not None:
        where = where & (carga_ar <= fecha_hasta)

    items, total_items = list_cheques_pendientes_page(db, where=where, page=page)
    return PaginatedMovimientosResponse(
        items=[movimiento_to_response(item, current_user) for item in items],
        page=page,
        page_size=PAGE_SIZE,
        total_items=total_items,
        total_pages=ceil(total_items / PAGE_SIZE) if total_items else 0,
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

    # T032: Compute fecha_override from fecha_manual at 09:00 AR (US3)
    # Backend applies fixed time; frontend sends YYYY-MM-DD only.
    fecha_override = None
    if payload.fecha_manual is not None:
        from datetime import datetime as _dt
        parsed = _dt.strptime(payload.fecha_manual, "%Y-%m-%d")
        fecha_override = _dt(
            parsed.year, parsed.month, parsed.day, 9, 0, 0,
            tzinfo=_ARGENTINA_TZ,
        )

    fecha_liquidacion = (
        date.fromisoformat(payload.fecha_liquidacion)
        if payload.fecha_liquidacion is not None
        else None
    )

    if payload.registrar_complementario:
        try:
            movimiento, complementario_mov = service.create_movimiento_pair(
                caja_id=caja_id,
                descripcion=payload.descripcion,
                monto=Decimal(payload.monto),
                tipo=payload.tipo,
                moneda=payload.moneda,
                fecha_override=fecha_override,
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
        fecha_override=fecha_override,
        instrumento=payload.instrumento,
        fecha_liquidacion=fecha_liquidacion,
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
        instrumento=movimiento.instrumento,
    )
    return MovimientoCreateResponse(
        movimiento=movimiento_to_response(movimiento, current_user),
        complementario=None,
    )


@router.post(
    "/{caja_id}/movimientos/{movimiento_id}/liquidar",
    response_model=MovimientoResponse,
)
def liquidar_cheque(
    caja_id: int,
    movimiento_id: int,
    current_user: Annotated[Usuario, Depends(require_role("secretaria"))],
    db: Annotated[Session, Depends(get_db)],
) -> MovimientoResponse:
    """Liquidate a pending cheque/echeque (manual, only for the Secretaria)."""
    caja = db.get(Caja, caja_id)
    if caja is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Caja no encontrada")

    service = MovimientoService(db)
    try:
        movimiento = service.liquidar_cheque(
            caja_id=caja_id,
            movimiento_id=movimiento_id,
            user=current_user,
        )
    except MovimientoNotFoundError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cheque no encontrado",
        ) from None
    except ChequeYaLiquidadoError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="El cheque ya fue liquidado",
        ) from None
    except ChequeAunNoLiquidableError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="El cheque todavía no alcanzó su fecha de liquidación",
        ) from None
    except Exception:
        db.rollback()
        logger.exception("cheque liquidation failed")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="No se pudo liquidar el cheque.",
        ) from None

    db.commit()
    db.refresh(movimiento)
    movimiento.caja = caja
    log_security_event(
        logger,
        "cheque_liquidated",
        username=current_user.username,
        rol=current_user.rol,
        caja_id=caja_id,
        movimiento_id=movimiento.id,
        instrumento=movimiento.instrumento,
        moneda=movimiento.moneda,
    )
    return movimiento_to_response(movimiento, current_user)


@router.post(
    "/{caja_id}/movimientos/{movimiento_id}/endosar",
    response_model=EndoseResponse,
)
def endosar_cheque(
    caja_id: int,
    movimiento_id: int,
    payload: EndosarChequeRequest,
    current_user: Annotated[Usuario, Depends(require_role("secretaria"))],
    db: Annotated[Session, Depends(get_db)],
) -> EndoseResponse:
    """Endorse a pending cheque to another caja (feature 011), atomically.

    The cheque is liquidated in its own caja and an inverse movement is created in the
    destination caja. Allowed at any time (it does not depend on the fecha de liquidación).
    """
    caja = db.get(Caja, caja_id)
    if caja is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Caja no encontrada")

    service = MovimientoService(db)
    try:
        result = service.endosar_cheque(
            caja_id=caja_id,
            movimiento_id=movimiento_id,
            caja_destino_id=payload.caja_destino_id,
            user=current_user,
        )
        db.flush()
    except MovimientoNotFoundError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cheque no encontrado",
        ) from None
    except CajaDestinoNotFoundError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Caja destino no encontrada",
        ) from None
    except EndoseDestinoInvalidoError as exc:
        db.rollback()
        raise HTTPException(
            status_code=422,
            detail=str(exc),
        ) from None
    except (ChequeYaLiquidadoError, IntegrityError):
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="El cheque ya fue liquidado o endosado",
        ) from None
    except Exception:
        db.rollback()
        logger.exception("cheque endorsement failed")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="No se pudo endosar el cheque.",
        ) from None

    db.commit()
    cheque = result.cheque
    destino = result.movimiento_destino
    db.refresh(cheque)
    db.refresh(destino)
    log_security_event(
        logger,
        "cheque_endorsed",
        username=current_user.username,
        rol=current_user.rol,
        caja_id=caja_id,
        caja_destino_id=destino.caja_id,
        movimiento_id=cheque.id,
        movimiento_destino_id=destino.id,
        instrumento=cheque.instrumento,
        moneda=cheque.moneda,
    )
    return EndoseResponse(
        cheque=movimiento_to_response(cheque, current_user),
        movimiento_destino=movimiento_to_response(destino, current_user),
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
            instrumento=payload.instrumento,
            fecha_liquidacion=(
                date.fromisoformat(payload.fecha_liquidacion)
                if payload.fecha_liquidacion is not None
                else None
            ),
        )
    except MovimientoNotFoundError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Movimiento no encontrado",
        ) from None
    except MovimientoEndosadoError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Un endose no se puede modificar",
        ) from None
    except ValueError as exc:
        db.rollback()
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
        instrumento=movimiento.instrumento,
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
        deleted = service.delete_movimiento(
            caja_id=caja_id,
            movimiento_id=movimiento_id,
            user=current_user,
        )
    except MovimientoNotFoundError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Movimiento no encontrado",
        ) from None
    except MovimientoEndosadoError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Un endose no se puede eliminar",
        ) from None

    db.commit()
    log_security_event(
        logger,
        "movimiento_deleted",
        username=current_user.username,
        rol=current_user.rol,
        caja_id=caja_id,
        movimiento_id=movimiento_id,
        instrumento=deleted.instrumento,
    )
