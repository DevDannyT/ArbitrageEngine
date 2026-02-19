import re
from typing import Dict, Any, List

BANNED = [
    "proxy", "custom", "digital", "download", "code", "mtgo",
    "lot", "bundle", "playset", "booster", "box", "case", "empty",
    "replica", "reprint", "fake",
]

def _norm(s: str) -> str:
    s = (s or "").lower()
    s = re.sub(r"[^a-z0-9/ ]+", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s

def build_ebay_query(card: Dict[str, Any]) -> str:
    # Build a query that usually performs well for collectibles
    name = card.get("name") or ""
    set_name = card.get("set") or ""
    number = card.get("number") or ""
    parts = [name]
    if set_name:
        parts.append(set_name)
    if number:
        parts.append(number)
    return " ".join([p for p in parts if p]).strip()

def score_ebay_listing(card: Dict[str, Any], item: Dict[str, Any]) -> Dict[str, Any]:
    """
    Explainable confidence score based on simple signals:
    - name tokens overlap
    - set tokens overlap
    - number appears (strong)
    - banned words (strong negative)
    """
    title_raw = item.get("title") or ""
    title = _norm(title_raw)

    reasons = []
    confidence = 0.0

    # banned words
    for w in BANNED:
        if w in title:
            reasons.append({"signal": "banned_word", "value": w, "ok": False})
            return {"confidence": 0.0, "reasons": reasons}

    reasons.append({"signal": "banned_word", "value": "none", "ok": True})

    card_name = _norm(card.get("name") or "")
    card_set = _norm(card.get("set") or "")
    card_num = _norm(card.get("number") or "")

    name_tokens = [t for t in card_name.split(" ") if t and len(t) > 2]
    set_tokens = [t for t in card_set.split(" ") if t and len(t) > 2]

    # name overlap
    name_hits = sum(1 for t in name_tokens if t in title)
    name_ratio = name_hits / max(1, min(len(name_tokens), 6))
    confidence += 0.55 * min(1.0, name_ratio)
    reasons.append({"signal": "name_tokens", "hits": name_hits, "total": len(name_tokens), "ok": name_hits > 0})

    # set overlap (lighter weight)
    set_hits = sum(1 for t in set_tokens if t in title)
    set_ratio = set_hits / max(1, min(len(set_tokens), 6))
    confidence += 0.20 * min(1.0, set_ratio)
    reasons.append({"signal": "set_tokens", "hits": set_hits, "total": len(set_tokens), "ok": (not card_set) or set_hits > 0})

    # number match (very strong)
    if card_num:
        # handle formats like 4/102
        if card_num in title:
            confidence += 0.35
            reasons.append({"signal": "card_number", "value": card_num, "ok": True})
        else:
            # sometimes number appears without slash
            num_flat = card_num.replace("/", " ")
            ok = any(part.isdigit() and part in title for part in num_flat.split(" "))
            if ok:
                confidence += 0.20
            reasons.append({"signal": "card_number", "value": card_num, "ok": ok})
    else:
        reasons.append({"signal": "card_number", "value": None, "ok": True})

    confidence = max(0.0, min(1.0, confidence))
    return {"confidence": confidence, "reasons": reasons}
