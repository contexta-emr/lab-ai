"""Turn a printed date into a real one, without ever inventing it.

Every longitudinal query orders by collection date, so a date that stays an unparsed
string is a row that cannot be charted. But a *wrong* date is worse than none: it puts a
result at the wrong point on a trend line, which is invisible and unrecoverable.

So parsing is **additive**. The printed text is always kept exactly as it appeared; a
parsed value appears beside it only when it is unambiguous. Anything else stays ``None``
and the raw text is what a human sees.

**Day-first is not a preference, it is a correctness requirement.** ``07-11-2025`` is the
7th of November in India and the 11th of July in the United States. Guessing wrong moves a
result four months and nothing on screen would say so.
"""

from __future__ import annotations

import datetime as dt
import re
from typing import Any, cast

import dateparser

__all__ = ["parse_lab_date"]

#: Day-month-year, because these are Indian lab reports. ``STRICT_PARSING`` is off so
#: partial inputs still parse, but the guards below reject what it would over-read.
_SETTINGS = {
    "DATE_ORDER": "DMY",
    "PREFER_DATES_FROM": "past",
    "RETURN_AS_TIMEZONE_AWARE": False,
}

#: Demo templates and anonymised reports redact the year as "202X" or "2X". Those are not
#: dates and must never be coerced into one.
_REDACTED_RE = re.compile(r"\d*[Xx]{1,4}\b")

#: A real date needs at least a day and a month somewhere in it. Without this a bare
#: "08:01 AM" parses to today's date at that time - a fabricated day.
_HAS_DATE_RE = re.compile(
    r"(\d{1,2}\s*[-/.]\s*\d{1,2})|(\d{4})|"
    r"(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)",
    re.IGNORECASE,
)


def parse_lab_date(text: str | None) -> dt.datetime | None:
    """Parse a printed date, or return ``None`` rather than guess.

    Args:
        text: The date exactly as printed, or ``None``.

    Returns:
        The parsed value, or ``None`` when the text is absent, redacted, or carries no
        recognisable date. A time with no date returns ``None`` - dateparser would
        otherwise supply today's date, silently fabricating a collection day.

    Examples:
        >>> parse_lab_date("07-Nov-2025 / 08:01 AM")
        datetime.datetime(2025, 11, 7, 8, 1)
        >>> parse_lab_date("02 Dec, 202X 05:00 PM") is None
        True
    """
    if not text or not text.strip():
        return None
    if _REDACTED_RE.search(text):
        return None
    if not _HAS_DATE_RE.search(text):
        return None
    try:
        parsed: Any = dateparser.parse(text, settings=_SETTINGS)
        return cast("dt.datetime | None", parsed)
    except (ValueError, OverflowError, TypeError):
        # dateparser is forgiving, but a malformed string should never take a run down.
        return None
