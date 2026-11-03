from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.api.deps import require_role
from app.core.dates import ARGENTINA_TZ
from app.core.filenames import build_informe_filename
from app.core.logging import get_logger, log_security_event
from app.db.session import get_db
from app.models.usuario import Usuario
from app.schemas.informe import InformePdfRequest, InformeTipo
from app.services.informe_service import InformeDateRangeError, InformeService
from app.services.pdf_informe_renderer import (
    InformeCajaMetadata,
    InformePlazoFijoMetadata,
    render_caja_pdf,
    render_plazo_fijo_pdf,
)

router = APIRouter()
logger = get_logger(__name__)


@router.post("/pdf")
def generate_informe_pdf(
    payload: InformePdfRequest,
    current_user: Annotated[Usuario, Depends(require_role("secretaria", "escribano"))],
    db: Annotated[Session, Depends(get_db)],
) -> StreamingResponse:
    service = InformeService(db)

    caja = service.get_caja(payload.caja_id)
    if caja is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Caja no encontrada")

    try:
        date_from, date_to = service.resolve_date_range(payload)
    except InformeDateRangeError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc

    generated_at = datetime.now(ARGENTINA_TZ)

    if payload.tipo == InformeTipo.CAJA:
        movimientos = service.fetch_movimientos_informe(
            caja_id=payload.caja_id,
            date_from=date_from,
            date_to=date_to,
        )
        saldo_cierre_ars = service.compute_saldo_cierre_by_moneda(movimientos, "ARS")
        saldo_cierre_usd = service.compute_saldo_cierre_by_moneda(movimientos, "USD")
        saldo_actual_ars = service.fetch_saldo_ars(payload.caja_id)
        saldo_actual_usd = service.fetch_saldo_usd(payload.caja_id)
        # Current state (not filtered by period): pending cheques and projected balance.
        cheques_pendientes, cheques_pendientes_total = service.fetch_cheques_pendientes(
            payload.caja_id
        )
        saldo_futuro = service.fetch_saldo_futuro(payload.caja_id)
        metadata = InformeCajaMetadata(
            caja_nombre=caja.nombre,
            date_from=date_from,
            date_to=date_to,
            generated_at=generated_at,
        )
        pdf_bytes = render_caja_pdf(
            metadata=metadata,
            movimientos=movimientos,
            saldo_cierre_ars=saldo_cierre_ars,
            saldo_cierre_usd=saldo_cierre_usd,
            saldo_actual_ars=saldo_actual_ars,
            saldo_actual_usd=saldo_actual_usd,
            cheques_pendientes=cheques_pendientes,
            cheques_pendientes_total=cheques_pendientes_total,
            saldo_futuro=saldo_futuro,
        )
    elif payload.tipo == InformeTipo.PLAZO_FIJO:
        plazos = service.fetch_plazos_informe(
            caja_id=payload.caja_id,
            date_from=date_from,
            date_to=date_to,
        )
        resumen = service.compute_resumen_plazos_filtrado(plazos)
        metadata = InformePlazoFijoMetadata(
            caja_nombre=caja.nombre,
            date_from=date_from,
            date_to=date_to,
            generated_at=generated_at,
        )
        pdf_bytes = render_plazo_fijo_pdf(
            metadata=metadata,
            plazos=plazos,
            resumen=resumen,
        )
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Tipo de informe no soportado",
        )

    filename = build_informe_filename(
        tipo=payload.tipo,
        caja_nombre=caja.nombre,
        modo=payload.modo,
        hasta_hoy=payload.hasta_hoy,
        mes=payload.mes,
        anio=payload.anio,
        date_from=date_from,
        date_to=date_to,
    )

    log_security_event(
        logger,
        "informe_generated",
        username=current_user.username,
        rol=current_user.rol,
        tipo=payload.tipo.value,
        caja_id=payload.caja_id,
        modo=payload.modo.value,
        hasta_hoy=payload.hasta_hoy,
    )

    return StreamingResponse(
        iter([pdf_bytes]),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
