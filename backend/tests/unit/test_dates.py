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
