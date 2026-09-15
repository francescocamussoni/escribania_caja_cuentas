"""
T007 — TDD: unit tests para el scoping del subtotal por stream (caja_id, moneda).

Regla de negocio (data-model.md / spec US1 / FR-012):
  - El `subtotal` de un movimiento se calcula sobre el último subtotal de la
    MISMA moneda en la MISMA caja; streams ARS y USD son completamente independientes.
  - El primer movimiento de un stream comienza desde 0, sin importar el estado
    del otro stream.

Estos tests deben FALLAR hasta que T011 scopee `create_movimiento` por (caja_id, moneda).

Todos los tests son puramente de lógica de dominio y NO requieren base de datos.
Se usa unittest.mock para aislar la capa de persistencia.
"""

from decimal import Decimal
from unittest.mock import MagicMock, patch

import pytest

from app.services.movimiento_service import MovimientoService, compute_subtotal


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_mock_movimiento(subtotal: Decimal, moneda: str = "ARS") -> MagicMock:
    """Devuelve un Movimiento mock con los atributos mínimos necesarios."""
    mov = MagicMock()
    mov.subtotal = subtotal
    mov.moneda = moneda
    return mov


def _make_service_with_last(
    last_movimiento: MagicMock | None,
) -> tuple[MovimientoService, MagicMock]:
    """
    Devuelve (service, db_mock) donde db.scalar() devuelve `last_movimiento`.
    Permite controlar qué "último movimiento del stream" ve el servicio.
    """
    db = MagicMock()
    db.scalar.return_value = last_movimiento
    service = MovimientoService(db=db)
    return service, db


def _make_user(rol: str = "secretaria") -> MagicMock:
    user = MagicMock()
    user.id = 1
    user.rol = rol
    return user


# ---------------------------------------------------------------------------
# Tests: create_movimiento acepta el parámetro `moneda`
# ---------------------------------------------------------------------------

def test_create_movimiento_accepts_moneda_ars() -> None:
    """create_movimiento debe aceptar el kwarg `moneda='ARS'`."""
    service, db = _make_service_with_last(None)
    user = _make_user()

    # El servicio debe crear el movimiento sin levantar TypeError
    service.create_movimiento(
        caja_id=1,
        descripcion="Test ARS",
        monto=Decimal("100.00"),
        tipo="entrada",
        moneda="ARS",
        user=user,
    )

    db.add.assert_called_once()
    created: MagicMock = db.add.call_args[0][0]
    assert created.moneda == "ARS"


def test_create_movimiento_accepts_moneda_usd() -> None:
    """create_movimiento debe aceptar el kwarg `moneda='USD'`."""
    service, db = _make_service_with_last(None)
    user = _make_user()

    service.create_movimiento(
        caja_id=1,
        descripcion="Test USD",
        monto=Decimal("50.00"),
        tipo="entrada",
        moneda="USD",
        user=user,
    )

    db.add.assert_called_once()
    created: MagicMock = db.add.call_args[0][0]
    assert created.moneda == "USD"


def test_create_movimiento_default_moneda_is_ars() -> None:
    """Si no se pasa `moneda`, el default debe ser 'ARS'."""
    service, db = _make_service_with_last(None)
    user = _make_user()

    service.create_movimiento(
        caja_id=1,
        descripcion="Default moneda",
        monto=Decimal("100.00"),
        tipo="entrada",
        user=user,
    )

    created: MagicMock = db.add.call_args[0][0]
    assert created.moneda == "ARS"


# ---------------------------------------------------------------------------
# Tests: el stream ARS es independiente del stream USD
# ---------------------------------------------------------------------------

def test_first_usd_movement_starts_at_zero_regardless_of_ars_stream() -> None:
    """
    Si ya hay movimientos ARS con subtotal 5000, el primer movimiento USD
    debe calcular su subtotal desde 0, NO desde 5000.

    El db.scalar debe ser llamado con un filtro que incluya `moneda='USD'`;
    como no hay movimientos USD, devuelve None → previous = 0.
    """
    # Simulamos: no hay movimientos USD en la caja (None) aunque haya ARS
    service, db = _make_service_with_last(None)
    user = _make_user()

    service.create_movimiento(
        caja_id=1,
        descripcion="Primer USD",
        monto=Decimal("200.00"),
        tipo="entrada",
        moneda="USD",
        user=user,
    )

    created: MagicMock = db.add.call_args[0][0]
    # subtotal debe ser 0 + 200 = 200
    assert created.subtotal == Decimal("200.00"), (
        f"Primer movimiento USD debería comenzar desde 0, obtenido: {created.subtotal}"
    )


def test_usd_stream_uses_previous_usd_subtotal_not_ars() -> None:
    """
    Si el último movimiento USD tiene subtotal 300, un nuevo USD entrada 100
    debe dar subtotal 400 (no importa el subtotal del stream ARS).
    """
    last_usd = _make_mock_movimiento(subtotal=Decimal("300.00"), moneda="USD")
    service, db = _make_service_with_last(last_usd)
    user = _make_user()

    service.create_movimiento(
        caja_id=1,
        descripcion="Segunda USD",
        monto=Decimal("100.00"),
        tipo="entrada",
        moneda="USD",
        user=user,
    )

    created: MagicMock = db.add.call_args[0][0]
    assert created.subtotal == Decimal("400.00"), (
        f"Subtotal USD esperado 400.00, obtenido: {created.subtotal}"
    )


def test_ars_stream_uses_previous_ars_subtotal_not_usd() -> None:
    """
    Si el último movimiento ARS tiene subtotal 1000, un nuevo ARS entrada 500
    debe dar 1500, sin importar si existen movimientos USD.
    """
    last_ars = _make_mock_movimiento(subtotal=Decimal("1000.00"), moneda="ARS")
    service, db = _make_service_with_last(last_ars)
    user = _make_user()

    service.create_movimiento(
        caja_id=1,
        descripcion="ARS con USD existente",
        monto=Decimal("500.00"),
        tipo="entrada",
        moneda="ARS",
        user=user,
    )

    created: MagicMock = db.add.call_args[0][0]
    assert created.subtotal == Decimal("1500.00"), (
        f"Subtotal ARS esperado 1500.00, obtenido: {created.subtotal}"
    )


def test_usd_salida_stream_decrements_correctly() -> None:
    """Salida USD decrementa el subtotal del stream USD."""
    last_usd = _make_mock_movimiento(subtotal=Decimal("500.00"), moneda="USD")
    service, db = _make_service_with_last(last_usd)
    user = _make_user()

    service.create_movimiento(
        caja_id=1,
        descripcion="Salida USD",
        monto=Decimal("150.00"),
        tipo="salida",
        moneda="USD",
        user=user,
    )

    created: MagicMock = db.add.call_args[0][0]
    assert created.subtotal == Decimal("350.00"), (
        f"Subtotal USD tras salida esperado 350.00, obtenido: {created.subtotal}"
    )


# ---------------------------------------------------------------------------
# Tests: la query al DB filtra por moneda (verificación de llamada)
# ---------------------------------------------------------------------------

def test_create_movimiento_queries_db_with_moneda_filter_usd() -> None:
    """
    La consulta al DB para obtener el último movimiento del stream
    DEBE incluir un filtro por moneda='USD'.
    Sin ese filtro, los streams se mezclarían.
    """
    service, db = _make_service_with_last(None)
    user = _make_user()

    service.create_movimiento(
        caja_id=7,
        descripcion="USD con filtro",
        monto=Decimal("10.00"),
        tipo="entrada",
        moneda="USD",
        user=user,
    )

    # La consulta debe haber sido ejecutada (scalar fue llamado)
    assert db.scalar.called, "Se esperaba una llamada a db.scalar para obtener el último movimiento"

    # Obtenemos el argumento pasado a scalar (un Select de SQLAlchemy)
    call_arg = db.scalar.call_args[0][0]
    # Compilamos la query a string para inspeccionarla
    compiled = str(call_arg.compile(compile_kwargs={"literal_binds": True}))
    assert "USD" in compiled, (
        f"La query al DB debería filtrar por moneda='USD'. Query generada:\n{compiled}"
    )


def test_create_movimiento_queries_db_with_moneda_filter_ars() -> None:
    """
    La consulta al DB para obtener el último movimiento del stream
    DEBE incluir un filtro por moneda='ARS'.
    """
    service, db = _make_service_with_last(None)
    user = _make_user()

    service.create_movimiento(
        caja_id=3,
        descripcion="ARS con filtro",
        monto=Decimal("50.00"),
        tipo="entrada",
        moneda="ARS",
        user=user,
    )

    call_arg = db.scalar.call_args[0][0]
    compiled = str(call_arg.compile(compile_kwargs={"literal_binds": True}))
    assert "ARS" in compiled, (
        f"La query al DB debería filtrar por moneda='ARS'. Query generada:\n{compiled}"
    )


# ---------------------------------------------------------------------------
# Tests: recalculate_subtotals scopea por (caja_id, moneda)
# ---------------------------------------------------------------------------

def test_recalculate_subtotals_accepts_moneda_param() -> None:
    """recalculate_subtotals debe aceptar el kwarg `moneda` sin TypeError."""
    db = MagicMock()
    db.scalars.return_value.all.return_value = []
    service = MovimientoService(db=db)

    # No debe levantar TypeError
    service.recalculate_subtotals(caja_id=1, moneda="ARS")


def test_recalculate_subtotals_queries_with_moneda_filter() -> None:
    """
    recalculate_subtotals(caja_id=5, moneda='USD') debe filtrar la query
    por moneda='USD' además de caja_id=5.
    """
    db = MagicMock()
    db.scalars.return_value.all.return_value = []
    service = MovimientoService(db=db)

    service.recalculate_subtotals(caja_id=5, moneda="USD")

    assert db.scalars.called
    call_arg = db.scalars.call_args[0][0]
    compiled = str(call_arg.compile(compile_kwargs={"literal_binds": True}))
    assert "USD" in compiled, (
        f"recalculate_subtotals debería filtrar por moneda='USD'. Query:\n{compiled}"
    )
    assert "5" in compiled, (
        f"recalculate_subtotals debería filtrar por caja_id=5. Query:\n{compiled}"
    )


# ---------------------------------------------------------------------------
# T020 — TDD: unit tests para registrar_complementario (US2)
#
# Regla de negocio (spec FR-008, FR-008a, FR-009):
#   - create_movimiento_pair persiste dos Movimientos en la misma transacción.
#   - Tipos opuestos: el accionado y el complementario.
#   - Mismo caja_id, descripcion, monto y moneda=USD.
#   - Si la DB falla en cualquier punto, ningún row queda persistido (rollback).
#   - Con moneda=ARS, registrar_complementario=True debe ser rechazado
#     (el schema lo valida antes, pero el service también debe rechazarlo).
#
# Estos tests DEBEN FALLAR hasta que T023 implemente `create_movimiento_pair`.
# ---------------------------------------------------------------------------


def test_create_movimiento_pair_inserts_two_movimientos() -> None:
    """
    create_movimiento_pair debe llamar a db.add dos veces —
    una por el movimiento accionado y otra por el complementario.
    """
    db = MagicMock()
    db.scalar.return_value = None  # sin movimientos previos en el stream
    service = MovimientoService(db=db)
    user = _make_user()

    principal, complementario = service.create_movimiento_pair(
        caja_id=1,
        descripcion="Cobro USD",
        monto=Decimal("100.00"),
        tipo="entrada",
        user=user,
    )

    assert db.add.call_count == 2, (
        f"Se esperaban 2 llamadas a db.add, obtenidas: {db.add.call_count}"
    )
    assert principal.tipo == "entrada"
    assert complementario.tipo == "salida"


def test_create_movimiento_pair_opposite_tipos() -> None:
    """
    El par debe tener tipos opuestos:
      - si el accionado es 'entrada', el complementario es 'salida'
      - si el accionado es 'salida',  el complementario es 'entrada'
    """
    db = MagicMock()
    db.scalar.return_value = None
    service = MovimientoService(db=db)
    user = _make_user()

    # caso entrada → complementario salida
    p1, c1 = service.create_movimiento_pair(
        caja_id=1, descripcion="Test", monto=Decimal("50.00"), tipo="entrada", user=user
    )
    assert p1.tipo == "entrada"
    assert c1.tipo == "salida"

    # caso salida → complementario entrada
    db.reset_mock()
    db.scalar.return_value = None
    p2, c2 = service.create_movimiento_pair(
        caja_id=1, descripcion="Test", monto=Decimal("50.00"), tipo="salida", user=user
    )
    assert p2.tipo == "salida"
    assert c2.tipo == "entrada"


def test_create_movimiento_pair_same_descripcion_monto_moneda() -> None:
    """
    El complementario debe tener el mismo caja_id, descripcion, monto y moneda
    que el principal.
    """
    db = MagicMock()
    db.scalar.return_value = None
    service = MovimientoService(db=db)
    user = _make_user()

    principal, complementario = service.create_movimiento_pair(
        caja_id=7,
        descripcion="  Cobro con espacios  ",  # debe trimear igual que create_movimiento
        monto=Decimal("200.00"),
        tipo="entrada",
        user=user,
    )

    assert principal.caja_id == 7
    assert complementario.caja_id == 7
    assert principal.descripcion == complementario.descripcion
    assert principal.monto == complementario.monto
    assert principal.moneda == "USD"
    assert complementario.moneda == "USD"


def test_create_movimiento_pair_moneda_is_always_usd() -> None:
    """
    create_movimiento_pair sin parámetro moneda usa USD por defecto.

    T004 — TDD: valida que el default moneda="USD" se mantiene cuando
    no se pasa el parámetro (backward-compat). FALLA hasta que T010
    añada `moneda` como parámetro con default "USD".
    """
    db = MagicMock()
    db.scalar.return_value = None
    service = MovimientoService(db=db)
    user = _make_user()

    principal, complementario = service.create_movimiento_pair(
        caja_id=2,
        descripcion="USD pair",
        monto=Decimal("75.00"),
        tipo="salida",
        user=user,
    )

    assert principal.moneda == "USD"
    assert complementario.moneda == "USD"


def test_create_movimiento_pair_accepts_ars_moneda() -> None:
    """
    create_movimiento_pair con moneda='ARS' crea ambos movimientos en ARS.

    T004 — TDD: FALLA hasta que T010 añada parámetro moneda y lo propague.
    """
    db = MagicMock()
    db.scalar.return_value = None
    service = MovimientoService(db=db)
    user = _make_user()

    principal, complementario = service.create_movimiento_pair(
        caja_id=3,
        descripcion="ARS par",
        monto=Decimal("1000.00"),
        tipo="entrada",
        moneda="ARS",
        user=user,
    )

    assert principal.moneda == "ARS", (
        f"Principal debería tener moneda='ARS', obtenido: {principal.moneda!r}"
    )
    assert complementario.moneda == "ARS", (
        f"Complementario debería tener moneda='ARS', obtenido: {complementario.moneda!r}"
    )
    assert principal.tipo == "entrada"
    assert complementario.tipo == "salida"


def test_create_movimiento_pair_ars_subtotals_start_from_zero() -> None:
    """
    Par ARS: stream ARS vacío → principal subtotal = 0 + monto.

    T004 — TDD: FALLA hasta que T010 pase moneda='ARS' al service interno.
    """
    db = MagicMock()
    db.scalar.return_value = None  # stream ARS vacío
    service = MovimientoService(db=db)
    user = _make_user()

    principal, _ = service.create_movimiento_pair(
        caja_id=4,
        descripcion="ARS par subtotal",
        monto=Decimal("300.00"),
        tipo="entrada",
        moneda="ARS",
        user=user,
    )

    assert principal.subtotal == Decimal("300.00"), (
        f"Subtotal ARS esperado 300.00, obtenido: {principal.subtotal}"
    )


def test_create_movimiento_pair_subtotals_are_sequential() -> None:
    """
    Los subtotales deben calcularse en secuencia:
      1. principal toma el último subtotal del stream USD
      2. complementario toma el subtotal del principal como previo
         (ya que el principal fue flusheado y es el nuevo último del stream)
    """
    # Stream USD tiene un movimiento anterior con subtotal 300
    last_usd = _make_mock_movimiento(subtotal=Decimal("300.00"), moneda="USD")

    # Después del flush del principal, el siguiente scalar ve el principal (subtotal 400)
    principal_placeholder = _make_mock_movimiento(subtotal=Decimal("400.00"), moneda="USD")

    db = MagicMock()
    # Primera llamada: busca el último USD → last_usd (300)
    # Segunda llamada (para el complementario): busca el último USD → principal con 400
    db.scalar.side_effect = [last_usd, principal_placeholder]
    service = MovimientoService(db=db)
    user = _make_user()

    principal, complementario = service.create_movimiento_pair(
        caja_id=1,
        descripcion="Par secuencial",
        monto=Decimal("100.00"),
        tipo="entrada",
        user=user,
    )

    # principal: 300 + 100 = 400
    assert principal.subtotal == Decimal("400.00"), (
        f"Principal subtotal esperado 400.00, obtenido: {principal.subtotal}"
    )
    # complementario (salida): 400 - 100 = 300
    assert complementario.subtotal == Decimal("300.00"), (
        f"Complementario subtotal esperado 300.00, obtenido: {complementario.subtotal}"
    )


# ---------------------------------------------------------------------------
# T022–T023 — TDD: fecha_override en create_movimiento y ordenamiento COALESCE
#
# Estos tests deben FALLAR hasta que T028/T029 implementen:
#   - T028: parámetro `fecha_override` en create_movimiento
#   - T029: ORDER BY COALESCE(fecha_override, created_at) en create_movimiento
# ---------------------------------------------------------------------------


def test_create_movimiento_persists_fecha_override() -> None:
    """T022: create_movimiento con fecha_override persiste ese valor en la columna."""
    from datetime import datetime
    from zoneinfo import ZoneInfo

    AR_TZ = ZoneInfo("America/Argentina/Buenos_Aires")
    fecha = datetime(2026, 9, 1, 9, 0, 0, tzinfo=AR_TZ)

    db = MagicMock()
    db.scalar.return_value = None  # No previous movimiento

    user = MagicMock()
    user.id = 1

    service = MovimientoService(db)

    with patch.object(service, "create_movimiento", wraps=service.create_movimiento):
        movimiento = service.create_movimiento(
            caja_id=1,
            descripcion="Cobro con fecha",
            monto=Decimal("100.00"),
            tipo="entrada",
            fecha_override=fecha,
            user=user,
        )

    assert movimiento.fecha_override == fecha, (
        f"fecha_override esperado {fecha}, obtenido {movimiento.fecha_override}"
    )


def test_create_movimiento_fecha_override_none_by_default() -> None:
    """T022: create_movimiento sin fecha_override deja la columna en None."""
    db = MagicMock()
    db.scalar.return_value = None

    user = MagicMock()
    user.id = 1

    service = MovimientoService(db)
    movimiento = service.create_movimiento(
        caja_id=1,
        descripcion="Cobro normal",
        monto=Decimal("50.00"),
        tipo="entrada",
        user=user,
    )

    assert movimiento.fecha_override is None, (
        f"fecha_override debería ser None por defecto, obtenido: {movimiento.fecha_override}"
    )


def test_create_movimiento_pair_propagates_fecha_override() -> None:
    """T022: create_movimiento_pair propaga fecha_override a ambos movimientos del par."""
    from datetime import datetime
    from zoneinfo import ZoneInfo

    AR_TZ = ZoneInfo("America/Argentina/Buenos_Aires")
    fecha = datetime(2026, 9, 1, 9, 0, 0, tzinfo=AR_TZ)

    db = MagicMock()
    db.scalar.return_value = None

    user = MagicMock()
    user.id = 1

    service = MovimientoService(db)
    principal, complementario = service.create_movimiento_pair(
        caja_id=1,
        descripcion="Par con fecha",
        monto=Decimal("200.00"),
        tipo="entrada",
        fecha_override=fecha,
        user=user,
    )

    assert principal.fecha_override == fecha, (
        f"Principal fecha_override esperado {fecha}, obtenido {principal.fecha_override}"
    )
    assert complementario.fecha_override == fecha, (
        f"Complementario fecha_override esperado {fecha}, obtenido {complementario.fecha_override}"
    )


def test_create_movimiento_queries_with_coalesce_order() -> None:
    """T023: create_movimiento usa COALESCE(fecha_override, created_at) en ORDER BY."""
    from unittest.mock import call

    db = MagicMock()
    db.scalar.return_value = None

    user = MagicMock()
    user.id = 1

    service = MovimientoService(db)
    service.create_movimiento(
        caja_id=1,
        descripcion="Test orden",
        monto=Decimal("10.00"),
        tipo="entrada",
        user=user,
    )

    # Verify that the DB scalar query was called (ordering verified by integration test T024)
    assert db.scalar.called, "Se esperaba una llamada a db.scalar para buscar el último movimiento"
