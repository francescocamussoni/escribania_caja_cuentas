import json
import logging

from app.core.logging import JsonLogFormatter, _sanitize_context, log_security_event


def test_sanitize_context_redacts_sensitive_fields() -> None:
    payload = _sanitize_context(
        {
            "event": "auth_login_failed",
            "username": "admin",
            "password": "secret",
            "access_token": "token-value",
        }
    )

    assert payload["event"] == "auth_login_failed"
    assert payload["username"] == "admin"
    assert "password" not in payload
    assert "access_token" not in payload


def test_log_security_event_emits_structured_record(caplog) -> None:
    logger = logging.getLogger("test.security")
    caplog.set_level(logging.INFO)

    with caplog.at_level(logging.INFO):
        log_security_event(logger, "auth_login_success", username="admin", rol="secretaria")

    assert len(caplog.records) == 1
    record = caplog.records[0]
    assert record.getMessage() == "auth_login_success"
    assert record.context["username"] == "admin"
    assert record.context["rol"] == "secretaria"


def test_json_log_formatter_includes_context() -> None:
    record = logging.LogRecord(
        name="test",
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg="hello",
        args=(),
        exc_info=None,
    )
    record.context = {"event": "movimiento_created", "caja_id": 1}

    formatted = JsonLogFormatter().format(record)
    payload = json.loads(formatted)

    assert payload["message"] == "hello"
    assert payload["event"] == "movimiento_created"
    assert payload["caja_id"] == 1


# ---------------------------------------------------------------------------
# T081 — feature 010: higiene de logs de cheques (sin montos ni descripciones)
# ---------------------------------------------------------------------------

from datetime import date, datetime, timezone  # noqa: E402
from decimal import Decimal  # noqa: E402
from unittest.mock import MagicMock, patch  # noqa: E402

import app.models  # noqa: E402, F401
from app.api.routes import movimientos as movimientos_routes  # noqa: E402
from app.models.caja import Caja  # noqa: E402
from app.models.movimiento import Movimiento  # noqa: E402
from app.schemas.movimiento import CreateMovimientoRequest, UpdateMovimientoRequest  # noqa: E402

SECRET_DESCRIPTION = "DESCRIPCION-SENSIBLE-123"
SECRET_AMOUNT = "987654.32"
ALLOWED_KEYS = {
    "event",
    "username",
    "rol",
    "caja_id",
    "movimiento_id",
    "tipo",
    "moneda",
    "instrumento",
    "complementario_id",
}


def _user() -> MagicMock:
    user = MagicMock()
    user.id = 1
    user.username = "admin"
    user.rol = "secretaria"
    return user


def _caja() -> Caja:
    return Caja(id=3, nombre="Caja log", slug="caja-log", estado="activa")


def _cheque(*, liquidado: bool = False) -> Movimiento:
    mov = Movimiento(
        id=77,
        caja_id=3,
        descripcion=SECRET_DESCRIPTION,
        monto=Decimal(SECRET_AMOUNT),
        tipo="entrada",
        moneda="ARS",
        instrumento="cheque",
        fecha_liquidacion=date(2999, 1, 1),
        fecha_liquidado=datetime(2026, 1, 1, tzinfo=timezone.utc) if liquidado else None,
        subtotal=Decimal(SECRET_AMOUNT) if liquidado else None,
        created_by=1,
        created_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        caja=_caja(),
    )
    return mov


def _db() -> MagicMock:
    db = MagicMock()
    db.get.return_value = _caja()
    return db


def _security_contexts(caplog) -> list[dict]:
    return [
        record.context
        for record in caplog.records
        if isinstance(getattr(record, "context", None), dict)
    ]


def _assert_clean(contexts: list[dict]) -> None:
    assert contexts, "expected a security event to be logged"
    for context in contexts:
        assert set(context) <= ALLOWED_KEYS, set(context) - ALLOWED_KEYS
        rendered = json.dumps(context, default=str)
        assert SECRET_DESCRIPTION not in rendered
        assert SECRET_AMOUNT not in rendered
        assert context["username"] == "admin"
        assert context["rol"] == "secretaria"


def test_movimiento_created_event_has_no_amount_or_description(caplog) -> None:
    payload = CreateMovimientoRequest(
        descripcion=SECRET_DESCRIPTION,
        monto=SECRET_AMOUNT,
        tipo="entrada",
        instrumento="cheque",
        fecha_liquidacion="2999-01-01",
    )
    with patch.object(movimientos_routes, "MovimientoService") as service:
        service.return_value.create_movimiento.return_value = _cheque()
        with caplog.at_level(logging.INFO):
            movimientos_routes.create_movimiento(3, payload, _user(), _db())

    contexts = [c for c in _security_contexts(caplog) if c["event"] == "movimiento_created"]
    _assert_clean(contexts)
    assert contexts[0]["instrumento"] == "cheque"
    assert contexts[0]["movimiento_id"] == 77


def test_cheque_liquidated_event_has_no_amount_or_description(caplog) -> None:
    with patch.object(movimientos_routes, "MovimientoService") as service:
        service.return_value.liquidar_cheque.return_value = _cheque(liquidado=True)
        with caplog.at_level(logging.INFO):
            movimientos_routes.liquidar_cheque(3, 77, _user(), _db())

    contexts = [c for c in _security_contexts(caplog) if c["event"] == "cheque_liquidated"]
    _assert_clean(contexts)
    assert contexts[0]["caja_id"] == 3 and contexts[0]["movimiento_id"] == 77


def test_movimiento_updated_event_has_no_amount_or_description(caplog) -> None:
    payload = UpdateMovimientoRequest(descripcion=SECRET_DESCRIPTION, monto=SECRET_AMOUNT)
    with patch.object(movimientos_routes, "MovimientoService") as service:
        service.return_value.update_movimiento.return_value = _cheque()
        with caplog.at_level(logging.INFO):
            movimientos_routes.update_movimiento(3, 77, payload, _user(), _db())

    contexts = [c for c in _security_contexts(caplog) if c["event"] == "movimiento_updated"]
    _assert_clean(contexts)


def test_movimiento_deleted_event_has_no_amount_or_description(caplog) -> None:
    with patch.object(movimientos_routes, "MovimientoService") as service:
        service.return_value.delete_movimiento.return_value = _cheque()
        with caplog.at_level(logging.INFO):
            movimientos_routes.delete_movimiento(3, 77, _user(), _db())

    contexts = [c for c in _security_contexts(caplog) if c["event"] == "movimiento_deleted"]
    _assert_clean(contexts)
    assert contexts[0]["instrumento"] == "cheque"


def test_failed_liquidation_logs_no_amount_or_description(caplog) -> None:
    import pytest
    from fastapi import HTTPException

    with patch.object(movimientos_routes, "MovimientoService") as service:
        service.return_value.liquidar_cheque.side_effect = RuntimeError(
            f"fallo con {SECRET_DESCRIPTION}"
        )
        with caplog.at_level(logging.INFO):
            with pytest.raises(HTTPException) as excinfo:
                movimientos_routes.liquidar_cheque(3, 77, _user(), _db())

    assert excinfo.value.status_code == 500
    assert SECRET_DESCRIPTION not in str(excinfo.value.detail)
    # The generic error text must not leak amounts or descriptions either.
    for record in caplog.records:
        assert SECRET_AMOUNT not in record.getMessage()
