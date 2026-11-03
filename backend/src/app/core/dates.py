"""Calendar helpers for Argentina business rules."""

import calendar
from datetime import date, datetime
from zoneinfo import ZoneInfo

ARGENTINA_TZ = ZoneInfo("America/Argentina/Buenos_Aires")


def today_ar() -> date:
    """Today's calendar date in America/Argentina/Buenos_Aires."""
    return datetime.now(ARGENTINA_TZ).date()


def end_of_month(day: date) -> date:
    """Last calendar day of the month that contains `day`."""
    return date(day.year, day.month, calendar.monthrange(day.year, day.month)[1])
