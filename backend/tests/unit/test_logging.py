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
