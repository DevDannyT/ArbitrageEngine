from typing import List, Optional, Dict
import math

def _median(xs: List[float]) -> Optional[float]:
    if not xs:
        return None
    ys = sorted(xs)
    n = len(ys)
    mid = n // 2
    if n % 2 == 1:
        return ys[mid]
    return (ys[mid - 1] + ys[mid]) / 2.0

def _percentile(xs: List[float], p: float) -> Optional[float]:
    if not xs:
        return None
    ys = sorted(xs)
    if p <= 0:
        return ys[0]
    if p >= 1:
        return ys[-1]
    idx = (len(ys) - 1) * p
    lo = math.floor(idx)
    hi = math.ceil(idx)
    if lo == hi:
        return ys[lo]
    frac = idx - lo
    return ys[lo] * (1 - frac) + ys[hi] * frac

def summarize_prices(prices: List[float]) -> Dict:
    prices = [float(x) for x in prices if x is not None and x > 0]
    if not prices:
        return {"count": 0, "median": None, "p25": None, "p75": None, "iqr": None, "stdev": None}

    med = _median(prices)
    p25 = _percentile(prices, 0.25)
    p75 = _percentile(prices, 0.75)
    iqr = None if (p25 is None or p75 is None) else (p75 - p25)

    # sample stdev
    mean = sum(prices) / len(prices)
    var = sum((x - mean) ** 2 for x in prices) / max(1, (len(prices) - 1))
    stdev = math.sqrt(var) if var >= 0 else None

    return {
        "count": len(prices),
        "median": med,
        "p25": p25,
        "p75": p75,
        "iqr": iqr,
        "stdev": stdev,
        "min": min(prices),
        "max": max(prices),
    }
