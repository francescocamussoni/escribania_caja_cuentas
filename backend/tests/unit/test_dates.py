from datetime import date, datetime
from unittest.mock import patch

from app.core.dates import ARGENTINA_TZ, today_ar


def test_today_ar_returns_date() -> None:
    assert isinstance(today_ar(), date)


def test_today_ar_uses_argentina_calendar() -> None:
    late_ar = datetime(2026, 8, 5, 23, 30, tzinfo=ARGENTINA_TZ)
    with patch("app.core.dates.datetime") as mock_datetime:
        mock_datetime.now.return_value = late_ar
        assert today_ar() == date(2026, 8, 5)


def test_today_ar_calls_now_with_argentina_tz() -> None:
    with patch("app.core.dates.datetime") as mock_datetime:
        mock_datetime.now.return_value = datetime(2026, 12, 31, 10, 0, tzinfo=ARGENTINA_TZ)
        today_ar()
        mock_datetime.now.assert_called_once_with(ARGENTINA_TZ)


# ---------------------------------------------------------------------------
# T004 — end_of_month (feature 010: categoría "Próximos a liquidar este mes")
# ---------------------------------------------------------------------------

import pytest  # noqa: E402

from app.core.dates import end_of_month  # noqa: E402


@pytest.mark.parametrize(
    ("given", "expected"),
    [
        (date(2026, 1, 1), date(2026, 1, 31)),
        (date(2026, 2, 10), date(2026, 2, 28)),
        (date(2028, 2, 1), date(2028, 2, 29)),  # año bisiesto
        (date(2026, 4, 30), date(2026, 4, 30)),
        (date(2026, 10, 21), date(2026, 10, 31)),
        (date(2026, 12, 15), date(2026, 12, 31)),
    ],
)
def test_end_of_month(given: date, expected: date) -> None:
    assert end_of_month(given) == expected
