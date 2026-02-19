from typing import List, Dict, Any

def rank_opportunities(opps: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Score = profit_usd * confidence * (1 + discount)
    """
    ranked = []
    for o in opps:
        prof = o["economics"]["profit"]
        conf = o["match"]["confidence"]
        discount = o.get("discount", 0.0)
        score = prof * conf * (1.0 + discount)
        ranked.append({**o, "score": score})

    ranked.sort(key=lambda x: (x["score"], x["economics"]["profit"]), reverse=True)
    return ranked
