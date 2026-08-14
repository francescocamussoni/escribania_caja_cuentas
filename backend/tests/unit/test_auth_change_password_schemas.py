"""Unit tests for change-password request schemas (T008)."""

import pytest
from pydantic import ValidationError

from app.schemas.auth import (
    ChangePasswordAuthenticatedRequest,
    ChangePasswordPublicRequest,
)


def test_public_change_password_accepts_valid_payload() -> None:
    payload = ChangePasswordPublicRequest(
        username="admin",
        current_password="admin",
        new_password="NuevaClave1",
        new_password_confirm="NuevaClave1",
    )
    assert payload.username == "admin"
    assert payload.new_password == "NuevaClave1"


def test_public_change_password_rejects_confirm_mismatch() -> None:
    with pytest.raises(ValidationError):
        ChangePasswordPublicRequest(
            username="admin",
            current_password="admin",
            new_password="NuevaClave1",
            new_password_confirm="OtraClave12",
        )


def test_public_change_password_rejects_short_new_password() -> None:
    with pytest.raises(ValidationError):
        ChangePasswordPublicRequest(
            username="admin",
            current_password="admin",
            new_password="short",
            new_password_confirm="short",
        )


def test_public_change_password_rejects_extra_fields() -> None:
    with pytest.raises(ValidationError):
        ChangePasswordPublicRequest.model_validate(
            {
                "username": "admin",
                "current_password": "admin",
                "new_password": "NuevaClave1",
                "new_password_confirm": "NuevaClave1",
                "user_id": 1,
            }
        )


def test_authenticated_change_password_has_no_username() -> None:
    assert "username" not in ChangePasswordAuthenticatedRequest.model_fields
    payload = ChangePasswordAuthenticatedRequest(
        current_password="admin",
        new_password="NuevaClave1",
        new_password_confirm="NuevaClave1",
    )
    assert payload.new_password == "NuevaClave1"
