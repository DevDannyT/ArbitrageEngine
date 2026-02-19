from typing import List, Dict, Any

def rank_opportunities(opps: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Score = profit_usd * confidence * liquidity_factor
    liquidity_factor is simple: 1.0 for now (later we can use #matches).
    """
    ranked = []
    for o in opps:
        prof = o["economics"]["profit"]
        conf = o["match"]["confidence"]
        score = prof * conf * 1.0
        ranked.append({**o, "score": score})

    ranked.sort(key=lambda x: (x["score"], x["economics"]["profit"]), reverse=True)
    return ranked
