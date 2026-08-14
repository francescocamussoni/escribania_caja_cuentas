import re
import unicodedata
from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.logging import get_logger, log_security_event
from app.models.caja import Caja
from app.models.evento_configuracion_caja import EventoConfiguracionCaja
from app.models.movimiento import Movimiento
from app.models.usuario import Usuario

CAJA_ESTADO_ACTIVA = "activa"
CAJA_ESTADO_ARCHIVADA = "archivada"
_SLUG_SAFE = re.compile(r"[^a-z0-9]+")
logger = get_logger(__name__)


class CajaDuplicateError(ValueError):
    """Ya existe una caja con el mismo nombre (activa o archivada)."""


class CajaNotFoundError(LookupError):
    """La caja indicada no existe."""


def normalize_caja_nombre(nombre: str) -> str:
    return " ".join(nombre.split())


def _nombre_key(nombre: str) -> str:
    return normalize_caja_nombre(nombre).casefold()


def slugify_caja_nombre(nombre: str) -> str:
    decomposed = unicodedata.normalize("NFKD", normalize_caja_nombre(nombre))
    ascii_name = decomposed.encode("ascii", "ignore").decode("ascii")
    slug = _SLUG_SAFE.sub("-", ascii_name.casefold()).strip("-")
    return slug or "caja"


def _record_event(
    db: Session,
    *,
    caja_id: int | None,
    accion: str,
    resultado: str,
    actor: Usuario,
    detalle: str | None = None,
) -> None:
    db.add(
        EventoConfiguracionCaja(
            caja_id=caja_id,
            accion=accion,
            resultado=resultado,
            actor_user_id=actor.id,
            detalle=detalle,
        )
    )


def _find_by_nombre_key(db: Session, nombre: str) -> Caja | None:
    target = _nombre_key(nombre)
    cajas = db.scalars(select(Caja)).all()
    for caja in cajas:
        if _nombre_key(caja.nombre) == target:
            return caja
    return None


def _unique_slug(db: Session, base_slug: str) -> str:
    slug = base_slug
    suffix = 2
    while db.scalar(select(Caja.id).where(Caja.slug == slug)) is not None:
        slug = f"{base_slug}-{suffix}"
        suffix += 1
    return slug


def create_caja(db: Session, *, nombre: str, actor: Usuario) -> Caja:
    cleaned = normalize_caja_nombre(nombre)
    if not cleaned:
        raise ValueError("nombre no puede estar vacío")

    if _find_by_nombre_key(db, cleaned) is not None:
        _record_event(
            db,
            caja_id=None,
            accion="crear",
            resultado="rechazo",
            actor=actor,
            detalle="nombre_duplicado",
        )
        db.flush()
        raise CajaDuplicateError("Ya existe una caja con ese nombre")

    caja = Caja(
        nombre=cleaned,
        slug=_unique_slug(db, slugify_caja_nombre(cleaned)),
        estado=CAJA_ESTADO_ACTIVA,
    )
    db.add(caja)
    db.flush()
    _record_event(
        db,
        caja_id=caja.id,
        accion="crear",
        resultado="exito",
        actor=actor,
    )
    db.flush()
    db.refresh(caja)
    log_security_event(
        logger,
        "caja_created",
        username=actor.username,
        caja_id=caja.id,
    )
    return caja


def archive_caja(db: Session, *, caja_id: int, actor: Usuario) -> Caja:
    caja = db.get(Caja, caja_id)
    if caja is None:
        _record_event(
            db,
            caja_id=None,
            accion="archivar",
            resultado="rechazo",
            actor=actor,
            detalle="caja_inexistente",
        )
        db.flush()
        raise CajaNotFoundError("Caja no encontrada")

    if caja.estado != CAJA_ESTADO_ARCHIVADA:
        caja.estado = CAJA_ESTADO_ARCHIVADA
        caja.archived_at = datetime.now(timezone.utc)
        caja.archived_by_user_id = actor.id

    _record_event(
        db,
        caja_id=caja.id,
        accion="archivar",
        resultado="exito",
        actor=actor,
    )
    db.flush()
    db.refresh(caja)
    log_security_event(
        logger,
        "caja_archived",
        username=actor.username,
        caja_id=caja.id,
    )
    return caja


def unarchive_caja(db: Session, *, caja_id: int, actor: Usuario) -> Caja:
    caja = db.get(Caja, caja_id)
    if caja is None:
        _record_event(
            db,
            caja_id=None,
            accion="desarchivar",
            resultado="rechazo",
            actor=actor,
            detalle="caja_inexistente",
        )
        db.flush()
        raise CajaNotFoundError("Caja no encontrada")

    if caja.estado != CAJA_ESTADO_ACTIVA:
        caja.estado = CAJA_ESTADO_ACTIVA
        caja.archived_at = None
        caja.archived_by_user_id = None

    _record_event(
        db,
        caja_id=caja.id,
        accion="desarchivar",
        resultado="exito",
        actor=actor,
    )
    db.flush()
    db.refresh(caja)
    log_security_event(
        logger,
        "caja_unarchived",
        username=actor.username,
        caja_id=caja.id,
    )
    return caja


def list_cajas_activas(db: Session) -> list[Caja]:
    return list(
        db.scalars(
            select(Caja)
            .where(Caja.estado == CAJA_ESTADO_ACTIVA)
            .order_by(Caja.id)
        ).all()
    )


def list_cajas_config(db: Session) -> list[Caja]:
    return list(db.scalars(select(Caja).order_by(Caja.id)).all())


def list_saldos_cajas_activas(db: Session) -> list[tuple[Caja, Decimal]]:
    rows: list[tuple[Caja, Decimal]] = []
    for caja in list_cajas_activas(db):
        last_subtotal = db.scalar(
            select(Movimiento.subtotal)
            .where(Movimiento.caja_id == caja.id)
            .order_by(Movimiento.created_at.desc(), Movimiento.id.desc())
            .limit(1)
        )
        rows.append(
            (caja, last_subtotal if last_subtotal is not None else Decimal("0.00"))
        )
    return rows
