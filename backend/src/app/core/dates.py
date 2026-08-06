"""Calendar helpers for Argentina business rules."""

from datetime import date, datetime
from zoneinfo import ZoneInfo

ARGENTINA_TZ = ZoneInfo("America/Argentina/Buenos_Aires")


def today_ar() -> date:
    """Today's calendar date in America/Argentina/Buenos_Aires."""
    return datetime.now(ARGENTINA_TZ).date()
