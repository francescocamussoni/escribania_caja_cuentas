"""Unit tests for plazo fijo list ordering (T004 — TDD, implement service in T011)."""

from datetime import date, datetime, timedelta, timezone

import pytest

from app.services.plazo_fijo_service import plazo_fijo_list_sort_key


def _ts(year: int, month: int, day: int, hour: int = 12) -> datetime:
    return datetime(year, month, day, hour, 0, tzinfo=timezone.utc)


@pytest.mark.parametrize(
    ("vencimiento", "created_at", "plazo_id"),
    [
        (date(2026, 8, 10), _ts(2026, 1, 1), 1),
        (date(2026, 8, 20), _ts(2026, 1, 2), 2),
        (date(2026, 7, 1), _ts(2026, 1, 3), 3),
        (date(2026, 6, 1), _ts(2026, 1, 4), 4),
    ],
)
def test_sort_key_future_before_vencidos(
    vencimiento: date,
    created_at: datetime,
    plazo_id: int,
) -> None:
    today = date(2026, 8, 6)
    key = plazo_fijo_list_sort_key(vencimiento, created_at, plazo_id, today)
    group = key[0]
    if vencimiento >= today:
        assert group == 0
    else:
        assert group == 1


def test_sort_future_by_vencimiento_ascending() -> None:
    today = date(2026, 8, 6)
    items = [
        (date(2026, 8, 20), _ts(2026, 1, 1), 2),
        (date(2026, 8, 10), _ts(2026, 1, 2), 1),
        (date(2026, 9, 1), _ts(2026, 1, 3), 3),
    ]
    sorted_items = sorted(
        items,
        key=lambda row: plazo_fijo_list_sort_key(row[0], row[1], row[2], today),
    )
    assert [row[0] for row in sorted_items] == [
        date(2026, 8, 10),
        date(2026, 8, 20),
        date(2026, 9, 1),
    ]


def test_sort_vencidos_by_vencimiento_descending() -> None:
    today = date(2026, 8, 6)
    items = [
        (date(2026, 6, 1), _ts(2026, 1, 1), 1),
        (date(2026, 7, 15), _ts(2026, 1, 2), 2),
        (date(2026, 5, 1), _ts(2026, 1, 3), 3),
    ]
    sorted_items = sorted(
        items,
        key=lambda row: plazo_fijo_list_sort_key(row[0], row[1], row[2], today),
    )
    assert [row[0] for row in sorted_items] == [
        date(2026, 7, 15),
        date(2026, 6, 1),
        date(2026, 5, 1),
    ]


def test_sort_full_list_future_then_vencidos() -> None:
    today = date(2026, 8, 6)
    items = [
        (date(2026, 7, 1), _ts(2026, 1, 1), 10),
        (date(2026, 8, 15), _ts(2026, 1, 2), 11),
        (date(2026, 6, 1), _ts(2026, 1, 3), 12),
        (date(2026, 8, 8), _ts(2026, 1, 4), 13),
    ]
    sorted_items = sorted(
        items,
        key=lambda row: plazo_fijo_list_sort_key(row[0], row[1], row[2], today),
    )
    assert [row[0] for row in sorted_items] == [
        date(2026, 8, 8),
        date(2026, 8, 15),
        date(2026, 7, 1),
        date(2026, 6, 1),
    ]


def test_sort_same_vencimiento_uses_created_at_desc() -> None:
    today = date(2026, 8, 6)
    venc = date(2026, 12, 31)
    older = (venc, _ts(2026, 1, 1), 1)
    newer = (venc, _ts(2026, 6, 1), 2)
    assert plazo_fijo_list_sort_key(*newer, today) < plazo_fijo_list_sort_key(*older, today)


def test_vencimiento_on_today_is_active() -> None:
    today = date(2026, 8, 6)
    key = plazo_fijo_list_sort_key(today, _ts(2026, 1, 1), 1, today)
    assert key[0] == 0
