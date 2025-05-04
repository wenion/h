from datetime import datetime, timezone
from typing import Optional, Union

"""Shared utility functions for manipulating dates and times."""


def utc_iso8601(datetime):
    """Convert a UTC datetime into an ISO8601 timestamp string."""

    if not datetime:
        return None

    return datetime.strftime("%Y-%m-%dT%H:%M:%S.%f+00:00")


def utc_us_style_date(datetime):
    """Convert a UTC datetime into a Month day, year (August 1, 1990)."""
    return "{d:%B} {d.day}, {d:%Y}".format(d=datetime)


def timestamp_ms_to_utc(ts_ms: Optional[Union[int, float]]) -> Optional[datetime]:
    """
    Converts a timestamp in milliseconds to a UTC datetime object.

    Args:
        ts_ms: Timestamp in milliseconds since epoch (can be None).

    Returns:
        A timezone-aware datetime object in UTC, or None if input is None.
    """
    if ts_ms is None:
        return None
    return datetime.fromtimestamp(ts_ms / 1000, tz=timezone.utc)
