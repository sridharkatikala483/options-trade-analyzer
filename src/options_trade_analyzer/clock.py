"""The one place the code asks what time it is, so a snapshot replay can freeze it at the recording time.

Live, today() is the local calendar date and now() is the current UTC time. A replay freezes both to
the moment the snapshot was recorded, so days to expiry, quote age and news age come out the same.
"""

import datetime as dt

_frozen: tuple[dt.datetime, dt.date] | None = None


def freeze(now_utc: dt.datetime, today_local: dt.date) -> None:
    global _frozen
    _frozen = (now_utc, today_local)


def unfreeze() -> None:
    global _frozen
    _frozen = None


def now() -> dt.datetime:
    return _frozen[0] if _frozen else dt.datetime.now(dt.timezone.utc)


def wall_now() -> dt.datetime:
    """The real current UTC time, never frozen: for logs (when a person ran or reviewed something), not for
    market math, which must use now()."""
    return dt.datetime.now(dt.timezone.utc)


def today() -> dt.date:
    return _frozen[1] if _frozen else dt.date.today()
