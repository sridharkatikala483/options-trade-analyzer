"""Price trend from daily closes: recent change, 50-day average and 3-month range.

Descriptive only: it says what the stock has done, not what it will do.
"""

import pandas as pd

ONE_MONTH, THREE_MONTHS, SMA_DAYS = 21, 63, 50  # trading days
SIDEWAYS_PCT = 2.0  # a 1-month move smaller than this is "sideways"


def price_trend(closes: pd.Series) -> dict:
    closes = closes.dropna()
    if len(closes) <= ONE_MONTH:
        return {"error": f"need more than {ONE_MONTH} daily closes, have {len(closes)}"}
    last = float(closes.iloc[-1])

    def change(days: int) -> float | None:
        return round((last / float(closes.iloc[-1 - days]) - 1) * 100, 1) if len(closes) > days else None

    sma = round(float(closes.tail(SMA_DAYS).mean()), 2) if len(closes) >= SMA_DAYS else None
    month = change(ONE_MONTH)
    if sma is not None and last > sma and month > SIDEWAYS_PCT:
        trend = "up"
    elif sma is not None and last < sma and month < -SIDEWAYS_PCT:
        trend = "down"
    else:
        trend = "sideways"
    recent = closes.tail(THREE_MONTHS)
    return {
        "last_close": round(last, 2),
        "change_1m_pct": month,
        "change_3m_pct": change(THREE_MONTHS),
        "sma_50": sma,
        "above_sma_50": None if sma is None else last > sma,
        "high_3m": round(float(recent.max()), 2),
        "low_3m": round(float(recent.min()), 2),
        "trend": trend,
    }
