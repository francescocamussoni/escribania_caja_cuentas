"""Unit tests for caja lifecycle (T004 — TDD, implement service in T008)."""

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.caja import Caja
from app.models.evento_configuracion_caja import EventoConfiguracionCaja
from app.models.usuario import Usuario
from app.services.caja_service import (
    CajaDuplicateError,
    CajaNotFoundError,
    archive_caja,
    create_caja,
    list_cajas_activas,
    list_cajas_config,
    unarchive_caja,
)


def _actor(db_session: Session) -> Usuario:
    user = db_session.scalar(select(Usuario).where(Usuario.username == "admin"))
    assert user is not None
    return user


def test_create_caja_is_activa(db_session: Session) -> None:
    actor = _actor(db_session)
    caja = create_caja(db_session, nombre="  Caja Nueva Test  ", actor=actor)

    assert caja.estado == "activa"
    assert caja.nombre == "Caja Nueva Test"
    assert caja.archived_at is None
    assert caja.archived_by_user_id is None

    event = db_session.scalar(
        select(EventoConfiguracionCaja)
        .where(EventoConfiguracionCaja.caja_id == caja.id)
        .order_by(EventoConfiguracionCaja.id.desc())
    )
    assert event is not None
    assert event.accion == "crear"
    assert event.resultado == "exito"
    assert event.actor_user_id == actor.id


def test_archive_transitions_activa_to_archivada(db_session: Session) -> None:
    actor = _actor(db_session)
    caja = create_caja(db_session, nombre="Caja A Archivar", actor=actor)

    archived = archive_caja(db_session, caja_id=caja.id, actor=actor)

    assert archived.id == caja.id
    assert archived.estado == "archivada"
    assert archived.archived_at is not None
    assert archived.archived_by_user_id == actor.id

    event = db_session.scalar(
        select(EventoConfiguracionCaja)
        .where(
            EventoConfiguracionCaja.caja_id == caja.id,
            EventoConfiguracionCaja.accion == "archivar",
        )
        .order_by(EventoConfiguracionCaja.id.desc())
    )
    assert event is not None
    assert event.resultado == "exito"


def test_archive_is_idempotent(db_session: Session) -> None:
    actor = _actor(db_session)
    caja = create_caja(db_session, nombre="Caja Idempotente", actor=actor)
    first = archive_caja(db_session, caja_id=caja.id, actor=actor)
    first_archived_at = first.archived_at

    second = archive_caja(db_session, caja_id=caja.id, actor=actor)

    assert second.estado == "archivada"
    assert second.archived_at == first_archived_at
    assert second.archived_by_user_id == actor.id


def test_unarchive_transitions_archivada_to_activa(db_session: Session) -> None:
    actor = _actor(db_session)
    caja = create_caja(db_session, nombre="Caja A Desarchivar", actor=actor)
    archive_caja(db_session, caja_id=caja.id, actor=actor)

    restored = unarchive_caja(db_session, caja_id=caja.id, actor=actor)

    assert restored.estado == "activa"
    assert restored.archived_at is None
    assert restored.archived_by_user_id is None
    assert restored.id in {caja.id for caja in list_cajas_activas(db_session)}

    event = db_session.scalar(
        select(EventoConfiguracionCaja)
        .where(
            EventoConfiguracionCaja.caja_id == caja.id,
            EventoConfiguracionCaja.accion == "desarchivar",
        )
        .order_by(EventoConfiguracionCaja.id.desc())
    )
    assert event is not None
    assert event.resultado == "exito"


def test_unarchive_is_idempotent(db_session: Session) -> None:
    actor = _actor(db_session)
    caja = create_caja(db_session, nombre="Caja Desarchivar Idemp", actor=actor)

    first = unarchive_caja(db_session, caja_id=caja.id, actor=actor)
    second = unarchive_caja(db_session, caja_id=caja.id, actor=actor)

    assert first.estado == "activa"
    assert second.estado == "activa"
    assert second.archived_at is None


def test_unarchive_unknown_caja_raises(db_session: Session) -> None:
    actor = _actor(db_session)
    with pytest.raises(CajaNotFoundError):
        unarchive_caja(db_session, caja_id=32767, actor=actor)


def test_create_rejects_duplicate_nombre_activa(db_session: Session) -> None:
    actor = _actor(db_session)
    create_caja(db_session, nombre="Caja Duplicada", actor=actor)

    with pytest.raises(CajaDuplicateError):
        create_caja(db_session, nombre="caja duplicada", actor=actor)


def test_create_rejects_duplicate_nombre_archivada(db_session: Session) -> None:
    actor = _actor(db_session)
    caja = create_caja(db_session, nombre="Caja Archivada Dup", actor=actor)
    archive_caja(db_session, caja_id=caja.id, actor=actor)

    with pytest.raises(CajaDuplicateError):
        create_caja(db_session, nombre="  CAJA ARCHIVADA DUP  ", actor=actor)


def test_archive_unknown_caja_raises(db_session: Session) -> None:
    actor = _actor(db_session)
    with pytest.raises(CajaNotFoundError):
        archive_caja(db_session, caja_id=32767, actor=actor)


def test_list_activas_excludes_archivadas(db_session: Session) -> None:
    actor = _actor(db_session)
    activa = create_caja(db_session, nombre="Lista Activa Unica", actor=actor)
    archivada = create_caja(db_session, nombre="Lista Archivada Unica", actor=actor)
    archive_caja(db_session, caja_id=archivada.id, actor=actor)

    activas = list_cajas_activas(db_session)
    ids = {caja.id for caja in activas}

    assert activa.id in ids
    assert archivada.id not in ids
    assert all(caja.estado == "activa" for caja in activas)


def test_list_config_includes_activas_and_archivadas(db_session: Session) -> None:
    actor = _actor(db_session)
    activa = create_caja(db_session, nombre="Config Activa Unica", actor=actor)
    archivada = create_caja(db_session, nombre="Config Archivada Unica", actor=actor)
    archive_caja(db_session, caja_id=archivada.id, actor=actor)

    config = list_cajas_config(db_session)
    ids = {caja.id for caja in config}

    assert activa.id in ids
    assert archivada.id in ids


def test_list_saldos_cajas_activas_excludes_archivadas(db_session: Session) -> None:
    from decimal import Decimal

    from app.services.caja_service import list_saldos_cajas_activas
    from app.services.movimiento_service import MovimientoService

    actor = _actor(db_session)
    service = MovimientoService(db_session)
    before = list_saldos_cajas_activas(db_session)
    before_total = sum((saldo_ars for _, saldo_ars, _usd in before), Decimal("0.00"))
    before_count = len(before)

    a = create_caja(db_session, nombre="Suma Activa A", actor=actor)
    b = create_caja(db_session, nombre="Suma Activa B", actor=actor)
    archived = create_caja(db_session, nombre="Suma Archivada", actor=actor)

    service.create_movimiento(
        caja_id=a.id,
        descripcion="entrada a",
        monto=Decimal("100.00"),
        tipo="entrada",
        user=actor,
    )
    service.create_movimiento(
        caja_id=b.id,
        descripcion="entrada b",
        monto=Decimal("25.50"),
        tipo="entrada",
        user=actor,
    )
    service.create_movimiento(
        caja_id=archived.id,
        descripcion="entrada archivada",
        monto=Decimal("999.00"),
        tipo="entrada",
        user=actor,
    )
    archive_caja(db_session, caja_id=archived.id, actor=actor)

    rows = list_saldos_cajas_activas(db_session)
    by_id = {caja.id: saldo_ars for caja, saldo_ars, _saldo_usd in rows}

    assert len(rows) == before_count + 2
    assert archived.id not in by_id
    assert by_id[a.id] == Decimal("100.00")
    assert by_id[b.id] == Decimal("25.50")
    assert sum(by_id.values(), Decimal("0.00")) == before_total + Decimal("125.50")
