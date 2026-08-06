from decimal import Decimal
from math import ceil
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_role
from app.core.logging import get_logger, log_security_event
from app.db.session import get_db
from app.models.usuario import Usuario
from app.schemas.caja import CajaResponse
from app.schemas.plazo_fijo import (
    CreatePlazoFijoRequest,
    PaginatedPlazosFijosResponse,
    PlazoFijoResponse,
    PlazosFijosResumenResponse,
    UpdatePlazoFijoRequest,
    format_decimal,
    plazo_fijo_to_response,
)
from app.services import plazo_fijo_service
from app.services.plazo_fijo_service import (
    PAGE_SIZE,
    PlazoFijoNotFoundError,
    PlazoFijoService,
)

router = APIRouter()
logger = get_logger(__name__)


@router.get(
    "/{caja_id}/plazos-fijos/resumen",
    response_model=PlazosFijosResumenResponse,
)
def get_plazos_fijos_resumen(
    caja_id: int,
    current_user: Annotated[Usuario, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> PlazosFijosResumenResponse:
    service = PlazoFijoService(db)
    caja = service.get_caja(caja_id)
    if caja is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Caja no encontrada")

    resumen = service.get_resumen(caja_id=caja_id)
    return PlazosFijosResumenResponse(
        caja=CajaResponse.model_validate(caja),
        total_monto_ingresado_activos=format_decimal(resumen.total_monto_ingresado_activos),
        total_monto_a_vencimiento_activos=format_decimal(
            resumen.total_monto_a_vencimiento_activos
        ),
    )


@router.get("/{caja_id}/plazos-fijos", response_model=PaginatedPlazosFijosResponse)
def list_plazos_fijos(
    caja_id: int,
    current_user: Annotated[Usuario, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query()] = PAGE_SIZE,
) -> PaginatedPlazosFijosResponse:
    if page_size != PAGE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="page_size debe ser 20",
        )

    service = PlazoFijoService(db)
    caja = service.get_caja(caja_id)
    if caja is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Caja no encontrada")

    plazos_fijos, total_items = service.list_plazos_fijos(
        caja_id=caja_id,
        page=page,
        page_size=PAGE_SIZE,
    )
    total_pages = ceil(total_items / PAGE_SIZE) if total_items else 0
    reference_today = plazo_fijo_service.today_ar()

    return PaginatedPlazosFijosResponse(
        items=[
            plazo_fijo_to_response(plazo_fijo, reference_today)
            for plazo_fijo in plazos_fijos
        ],
        page=page,
        page_size=PAGE_SIZE,
        total_items=total_items,
        total_pages=total_pages,
    )


@router.post(
    "/{caja_id}/plazos-fijos",
    response_model=PlazoFijoResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_plazo_fijo(
    caja_id: int,
    payload: CreatePlazoFijoRequest,
    current_user: Annotated[Usuario, Depends(require_role("secretaria"))],
    db: Annotated[Session, Depends(get_db)],
) -> PlazoFijoResponse:
    service = PlazoFijoService(db)
    caja = service.get_caja(caja_id)
    if caja is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Caja no encontrada")

    try:
        plazo_fijo = service.create_plazo_fijo(
            caja_id=caja_id,
            monto_ingresado=Decimal(payload.monto_ingresado),
            monto_a_vencimiento=Decimal(payload.monto_a_vencimiento),
            fecha_vencimiento=payload.fecha_vencimiento,
            user=current_user,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc

    db.commit()
    db.refresh(plazo_fijo)
    plazo_fijo.caja = caja
    reference_today = plazo_fijo_service.today_ar()
    log_security_event(
        logger,
        "plazo_fijo_created",
        username=current_user.username,
        rol=current_user.rol,
        caja_id=caja_id,
        plazo_fijo_id=plazo_fijo.id,
    )
    return plazo_fijo_to_response(plazo_fijo, reference_today)


@router.patch(
    "/{caja_id}/plazos-fijos/{plazo_fijo_id}",
    response_model=PlazoFijoResponse,
)
def update_plazo_fijo(
    caja_id: int,
    plazo_fijo_id: int,
    payload: UpdatePlazoFijoRequest,
    current_user: Annotated[Usuario, Depends(require_role("secretaria"))],
    db: Annotated[Session, Depends(get_db)],
) -> PlazoFijoResponse:
    service = PlazoFijoService(db)
    caja = service.get_caja(caja_id)
    if caja is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Caja no encontrada")

    try:
        plazo_fijo = service.update_plazo_fijo(
            caja_id=caja_id,
            plazo_fijo_id=plazo_fijo_id,
            monto_ingresado=(
                Decimal(payload.monto_ingresado) if payload.monto_ingresado is not None else None
            ),
            monto_a_vencimiento=(
                Decimal(payload.monto_a_vencimiento)
                if payload.monto_a_vencimiento is not None
                else None
            ),
            fecha_vencimiento=payload.fecha_vencimiento,
        )
    except PlazoFijoNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Plazo fijo no encontrado",
        ) from None
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc

    db.commit()
    db.refresh(plazo_fijo)
    plazo_fijo.caja = caja
    reference_today = plazo_fijo_service.today_ar()
    log_security_event(
        logger,
        "plazo_fijo_updated",
        username=current_user.username,
        rol=current_user.rol,
        caja_id=caja_id,
        plazo_fijo_id=plazo_fijo.id,
    )
    return plazo_fijo_to_response(plazo_fijo, reference_today)


@router.delete(
    "/{caja_id}/plazos-fijos/{plazo_fijo_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_plazo_fijo(
    caja_id: int,
    plazo_fijo_id: int,
    current_user: Annotated[Usuario, Depends(require_role("secretaria"))],
    db: Annotated[Session, Depends(get_db)],
) -> None:
    service = PlazoFijoService(db)
    caja = service.get_caja(caja_id)
    if caja is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Caja no encontrada")

    try:
        service.delete_plazo_fijo(caja_id=caja_id, plazo_fijo_id=plazo_fijo_id)
    except PlazoFijoNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Plazo fijo no encontrado",
        ) from None

    db.commit()
    log_security_event(
        logger,
        "plazo_fijo_deleted",
        username=current_user.username,
        rol=current_user.rol,
        caja_id=caja_id,
        plazo_fijo_id=plazo_fijo_id,
    )
