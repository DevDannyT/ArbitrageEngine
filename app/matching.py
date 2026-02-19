import re
from typing import Dict, Any, List

BANNED = [
    "proxy", "custom", "digital", "download", "code", "mtgo",
    "lot", "bundle", "playset", "booster", "box", "case", "empty",
    "replica", "fake",
]

def _norm(s: str) -> str:
    s = (s or "").lower()
    s = re.sub(r"[^a-z0-9/ ]+", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s

def build_market_query(game: str, q: str) -> str:
    q = q.strip()
    if game == "pokemon":
        # add tiny context, helps search quality
        return f"{q} pokemon card"
    if game == "mtg":
        return f"{q} magic the gathering card"
    return q

def score_listing_against_query(query: str, item: Dict[str, Any]) -> Dict[str, Any]:
    """
    Explainable confidence score based on query token hits.
    """
    title_raw = item.get("title") or ""
    title = _norm(title_raw)
    qn = _norm(query)

    reasons = []
    confidence = 0.0

    for w in BANNED:
        if w in title:
            reasons.append({"signal": "banned_word", "value": w, "ok": False})
            return {"confidence": 0.0, "reasons": reasons}

    reasons.append({"signal": "banned_word", "value": "none", "ok": True})

    tokens = [t for t in qn.split(" ") if t and len(t) > 2]
    if not tokens:
        return {"confidence": 0.0, "reasons": [{"signal": "query_tokens", "hits": 0, "total": 0, "ok": False}]}

    hits = sum(1 for t in tokens if t in title)
    ratio = hits / max(1, min(len(tokens), 8))

    # base score from token overlap
    confidence += 0.80 * min(1.0, ratio)

    # bonus for number-like patterns (e.g. 4/102, 1/1, 123)
    num_tokens = [t for t in tokens if any(c.isdigit() for c in t)]
    num_hit = any(t in title for t in num_tokens) if num_tokens else True
    if num_tokens and num_hit:
        confidence += 0.15
    reasons.append({"signal": "query_tokens", "hits": hits, "total": len(tokens), "ok": hits > 0})
    if num_tokens:
        reasons.append({"signal": "number_token", "value": "matched" if num_hit else "missing", "ok": num_hit})

    confidence = max(0.0, min(1.0, confidence))
    return {"confidence": confidence, "reasons": reasons}
