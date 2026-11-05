"""
T008 — TDD: `MovimientoService.endosar_cheque` (feature 011, US1).

Usa la sesión transaccional `db_session` (rollback al final): el servicio solo hace `flush`,
así que nada de lo que se crea acá persiste. Cada test crea cajas nuevas y vacías.
"""

from datetime import date, datetime, timezone
from decimal import Decimal
from uuid import uuid4

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.caja import Caja
from app.models.movimiento import Movimiento
from app.models.usuario import Usuario
from app.services.movimiento_service import (
    CajaDestinoNotFoundError,
    ChequeYaLiquidadoError,
    EndoseDestinoInvalidoError,
    MovimientoEndosadoError,
    MovimientoNotFoundError,
    MovimientoService,
)
from app.services.saldo_service import get_saldo_actual

FUTURO = date(2030, 1, 15)


@pytest.fixture
def user(db_session: Session) -> Usuario:
    found = db_session.scalar(select(Usuario).where(Usuario.username == "admin"))
    assert found is not None
    return found


def _caja(db: Session, estado: str = "activa") -> Caja:
    nombre = f"Endose {uuid4().hex[:12]}"
    caja = Caja(nombre=nombre, slug=nombre.lower().replace(" ", "-"), estado=estado)
    db.add(caja)
    db.flush()
    return caja


@pytest.fixture
def origen(db_session: Session) -> Caja:
    return _caja(db_session)


@pytest.fixture
def destino(db_session: Session) -> Caja:
    return _caja(db_session)


def _pendiente(
    service: MovimientoService,
    caja: Caja,
    user: Usuario,
    *,
    tipo: str = "entrada",
    monto: str = "500.00",
    moneda: str = "ARS",
    fecha: date = FUTURO,
    descripcion: str = "Cheque Banco Nación",
) -> Movimiento:
    return service.create_movimiento(
        caja_id=caja.id,
        descripcion=descripcion,
        monto=Decimal(monto),
        tipo=tipo,
        moneda=moneda,
        instrumento="cheque",
        fecha_liquidacion=fecha,
        user=user,
    )


def _saldo(db: Session, caja: Caja, moneda: str = "ARS") -> Decimal:
    return get_saldo_actual(db, caja.id, moneda)


def _destino_de(db: Session, cheque: Movimiento) -> Movimiento:
    found = db.scalar(select(Movimiento).where(Movimiento.endose_cheque_id == cheque.id))
    assert found is not None
    return found


# --------------------------------------------------------------------------- efecto contable


@pytest.mark.parametrize(
    ("tipo", "delta_origen", "tipo_destino", "delta_destino"),
    [
        ("entrada", Decimal("500.00"), "salida", Decimal("-500.00")),
        ("salida", Decimal("-500.00"), "entrada", Decimal("500.00")),
    ],
)
def test_endose_liquida_en_origen_y_crea_movimiento_inverso_en_destino(
    db_session, user, origen, destino, tipo, delta_origen, tipo_destino, delta_destino
) -> None:
    service = MovimientoService(db_session)
    cheque = _pendiente(service, origen, user, tipo=tipo)
    assert _saldo(db_session, origen) == Decimal("0")  # pendiente: sin impacto

    result = service.endosar_cheque(
        caja_id=origen.id, movimiento_id=cheque.id, caja_destino_id=destino.id, user=user
    )

    assert result.cheque.id == cheque.id
    assert _saldo(db_session, origen) == delta_origen
    assert _saldo(db_session, destino) == delta_destino
    # Neto entre cajas = 0
    assert _saldo(db_session, origen) + _saldo(db_session, destino) == Decimal("0")

    movimiento = result.movimiento_destino
    assert movimiento.tipo == tipo_destino
    assert movimiento.caja_id == destino.id
    assert movimiento.instrumento == "ninguno"
    assert movimiento.monto == Decimal("500.00")
    assert movimiento.moneda == "ARS"
    assert movimiento.endose_cheque_id == cheque.id
    assert movimiento.subtotal == delta_destino
    assert movimiento.created_by == user.id


def test_endose_marca_el_cheque_como_liquidado_y_endosado(
    db_session, user, origen, destino
) -> None:
    service = MovimientoService(db_session)
    cheque = _pendiente(service, origen, user)  # fecha de liquidación FUTURA

    result = service.endosar_cheque(
        caja_id=origen.id, movimiento_id=cheque.id, caja_destino_id=destino.id, user=user
    )

    assert result.cheque.fecha_liquidado is not None
    assert result.cheque.estado_cheque == "liquidado"
    assert result.cheque.endosado_a_caja_id == destino.id
    assert result.cheque.subtotal == Decimal("500.00")
    assert result.cheque.updated_by == user.id
    assert result.cheque.bloqueado_por_endose is True
    assert result.movimiento_destino.bloqueado_por_endose is True


def test_endose_funciona_con_fecha_de_liquidacion_vencida(
    db_session, user, origen, destino
) -> None:
    service = MovimientoService(db_session)
    cheque = _pendiente(service, origen, user)
    cheque.fecha_liquidacion = date(2020, 1, 1)  # simula un cheque ya apto
    db_session.flush()

    result = service.endosar_cheque(
        caja_id=origen.id, movimiento_id=cheque.id, caja_destino_id=destino.id, user=user
    )
    assert result.cheque.endosado is True


def test_endose_usa_streams_independientes_por_moneda(
    db_session, user, origen, destino
) -> None:
    service = MovimientoService(db_session)
    cheque = _pendiente(service, origen, user, moneda="USD", monto="250.00")

    service.endosar_cheque(
        caja_id=origen.id, movimiento_id=cheque.id, caja_destino_id=destino.id, user=user
    )

    assert _saldo(db_session, origen, "USD") == Decimal("250.00")
    assert _saldo(db_session, destino, "USD") == Decimal("-250.00")
    assert _saldo(db_session, origen, "ARS") == Decimal("0")
    assert _saldo(db_session, destino, "ARS") == Decimal("0")


def test_subtotal_del_destino_continua_el_stream_existente(
    db_session, user, origen, destino
) -> None:
    service = MovimientoService(db_session)
    service.create_movimiento(
        caja_id=destino.id, descripcion="previo", monto=Decimal("1000.00"),
        tipo="entrada", moneda="ARS", user=user,
    )
    cheque = _pendiente(service, origen, user, tipo="entrada", monto="300.00")

    result = service.endosar_cheque(
        caja_id=origen.id, movimiento_id=cheque.id, caja_destino_id=destino.id, user=user
    )

    assert result.movimiento_destino.subtotal == Decimal("700.00")
    assert _saldo(db_session, destino) == Decimal("700.00")


# --------------------------------------------------------------------------- descripción


def test_descripcion_del_destino_se_genera_en_el_servidor(
    db_session, user, origen, destino
) -> None:
    service = MovimientoService(db_session)
    cheque = _pendiente(service, origen, user, descripcion="Cheque 0001234")

    result = service.endosar_cheque(
        caja_id=origen.id, movimiento_id=cheque.id, caja_destino_id=destino.id, user=user
    )

    assert result.movimiento_destino.descripcion == (
        f"Endose cheque: Cheque 0001234 (Caja {origen.nombre})"
    )


def test_descripcion_del_destino_se_trunca_a_500(db_session, user, origen, destino) -> None:
    service = MovimientoService(db_session)
    cheque = _pendiente(service, origen, user, descripcion="x" * 500)

    result = service.endosar_cheque(
        caja_id=origen.id, movimiento_id=cheque.id, caja_destino_id=destino.id, user=user
    )

    assert len(result.movimiento_destino.descripcion) == 500
    assert result.movimiento_destino.descripcion.startswith("Endose cheque: xxx")


# --------------------------------------------------------------------------- errores


def test_cheque_inexistente_o_de_otra_caja(db_session, user, origen, destino) -> None:
    service = MovimientoService(db_session)
    cheque = _pendiente(service, origen, user)

    with pytest.raises(MovimientoNotFoundError):
        service.endosar_cheque(
            caja_id=origen.id, movimiento_id=999_999_999, caja_destino_id=destino.id, user=user
        )
    with pytest.raises(MovimientoNotFoundError):
        # el cheque pertenece a `origen`, no a `destino`
        service.endosar_cheque(
            caja_id=destino.id, movimiento_id=cheque.id, caja_destino_id=origen.id, user=user
        )


def test_movimiento_comun_no_se_puede_endosar(db_session, user, origen, destino) -> None:
    service = MovimientoService(db_session)
    comun = service.create_movimiento(
        caja_id=origen.id, descripcion="comun", monto=Decimal("10.00"),
        tipo="entrada", moneda="ARS", user=user,
    )
    with pytest.raises(MovimientoNotFoundError):
        service.endosar_cheque(
            caja_id=origen.id, movimiento_id=comun.id, caja_destino_id=destino.id, user=user
        )


def test_cheque_ya_liquidado_no_se_puede_endosar(db_session, user, origen, destino) -> None:
    service = MovimientoService(db_session)
    cheque = _pendiente(service, origen, user)
    cheque.fecha_liquidacion = date(2020, 1, 1)
    db_session.flush()
    service.liquidar_cheque(caja_id=origen.id, movimiento_id=cheque.id, user=user)

    with pytest.raises(ChequeYaLiquidadoError):
        service.endosar_cheque(
            caja_id=origen.id, movimiento_id=cheque.id, caja_destino_id=destino.id, user=user
        )
    assert _saldo(db_session, destino) == Decimal("0")


def test_segundo_endose_del_mismo_cheque_se_rechaza_sin_duplicar(
    db_session, user, origen, destino
) -> None:
    service = MovimientoService(db_session)
    cheque = _pendiente(service, origen, user)
    service.endosar_cheque(
        caja_id=origen.id, movimiento_id=cheque.id, caja_destino_id=destino.id, user=user
    )

    with pytest.raises(ChequeYaLiquidadoError):
        service.endosar_cheque(
            caja_id=origen.id, movimiento_id=cheque.id, caja_destino_id=destino.id, user=user
        )
    assert _saldo(db_session, origen) == Decimal("500.00")
    assert _saldo(db_session, destino) == Decimal("-500.00")


def test_liquidar_un_cheque_endosado_se_rechaza(db_session, user, origen, destino) -> None:
    service = MovimientoService(db_session)
    cheque = _pendiente(service, origen, user)
    service.endosar_cheque(
        caja_id=origen.id, movimiento_id=cheque.id, caja_destino_id=destino.id, user=user
    )
    with pytest.raises(ChequeYaLiquidadoError):
        service.liquidar_cheque(caja_id=origen.id, movimiento_id=cheque.id, user=user)


def test_destino_inexistente(db_session, user, origen) -> None:
    service = MovimientoService(db_session)
    cheque = _pendiente(service, origen, user)
    with pytest.raises(CajaDestinoNotFoundError):
        service.endosar_cheque(
            caja_id=origen.id, movimiento_id=cheque.id, caja_destino_id=32_000, user=user
        )
    assert cheque.fecha_liquidado is None


def test_destino_igual_al_origen(db_session, user, origen) -> None:
    service = MovimientoService(db_session)
    cheque = _pendiente(service, origen, user)
    with pytest.raises(EndoseDestinoInvalidoError):
        service.endosar_cheque(
            caja_id=origen.id, movimiento_id=cheque.id, caja_destino_id=origen.id, user=user
        )
    assert cheque.fecha_liquidado is None


def test_destino_archivada(db_session, user, origen) -> None:
    archivada = _caja(db_session, estado="archivada")
    service = MovimientoService(db_session)
    cheque = _pendiente(service, origen, user)
    with pytest.raises(EndoseDestinoInvalidoError):
        service.endosar_cheque(
            caja_id=origen.id, movimiento_id=cheque.id, caja_destino_id=archivada.id, user=user
        )
    assert cheque.fecha_liquidado is None


def test_si_falla_la_creacion_del_destino_no_queda_ningun_efecto(
    db_session, user, origen, destino, monkeypatch
) -> None:
    """Atomicidad: el servicio no hace commit, así que el rollback del llamador lo deshace todo."""
    service = MovimientoService(db_session)
    cheque = _pendiente(service, origen, user)
    cheque_id = cheque.id

    def boom(*args, **kwargs):
        raise RuntimeError("fallo simulado")

    monkeypatch.setattr(service, "create_movimiento", boom)

    savepoint = db_session.begin_nested()
    with pytest.raises(RuntimeError):
        service.endosar_cheque(
            caja_id=origen.id, movimiento_id=cheque_id, caja_destino_id=destino.id, user=user
        )
    savepoint.rollback()

    db_session.expire_all()
    persisted = db_session.get(Movimiento, cheque_id)
    assert persisted is not None
    assert persisted.fecha_liquidado is None
    assert persisted.endosado_a_caja_id is None
    assert persisted.subtotal is None
    assert (
        db_session.scalar(select(Movimiento).where(Movimiento.endose_cheque_id == cheque_id))
        is None
    )
    assert _saldo(db_session, origen) == Decimal("0")
    assert _saldo(db_session, destino) == Decimal("0")


# --------------------------------------------------------------------------- bloqueo FR-019


def test_cheque_endosado_no_se_edita_ni_elimina(db_session, user, origen, destino) -> None:
    service = MovimientoService(db_session)
    cheque = _pendiente(service, origen, user)
    service.endosar_cheque(
        caja_id=origen.id, movimiento_id=cheque.id, caja_destino_id=destino.id, user=user
    )

    with pytest.raises(MovimientoEndosadoError):
        service.update_movimiento(
            caja_id=origen.id, movimiento_id=cheque.id, user=user, descripcion="otra"
        )
    with pytest.raises(MovimientoEndosadoError):
        service.delete_movimiento(caja_id=origen.id, movimiento_id=cheque.id, user=user)
    assert _saldo(db_session, origen) == Decimal("500.00")


def test_movimiento_de_endose_no_se_edita_ni_elimina(db_session, user, origen, destino) -> None:
    service = MovimientoService(db_session)
    cheque = _pendiente(service, origen, user)
    service.endosar_cheque(
        caja_id=origen.id, movimiento_id=cheque.id, caja_destino_id=destino.id, user=user
    )
    movimiento = _destino_de(db_session, cheque)

    with pytest.raises(MovimientoEndosadoError):
        service.update_movimiento(
            caja_id=destino.id, movimiento_id=movimiento.id, user=user, monto=Decimal("1.00")
        )
    with pytest.raises(MovimientoEndosadoError):
        service.delete_movimiento(caja_id=destino.id, movimiento_id=movimiento.id, user=user)
    assert _saldo(db_session, destino) == Decimal("-500.00")


def test_cheque_liquidado_sin_endose_sigue_siendo_editable(
    db_session, user, origen
) -> None:
    service = MovimientoService(db_session)
    cheque = _pendiente(service, origen, user)
    cheque.fecha_liquidacion = date(2020, 1, 1)
    db_session.flush()
    service.liquidar_cheque(caja_id=origen.id, movimiento_id=cheque.id, user=user)

    updated = service.update_movimiento(
        caja_id=origen.id, movimiento_id=cheque.id, user=user, descripcion="corregido"
    )
    assert updated.descripcion == "corregido"
    service.delete_movimiento(caja_id=origen.id, movimiento_id=cheque.id, user=user)
    assert _saldo(db_session, origen) == Decimal("0")
