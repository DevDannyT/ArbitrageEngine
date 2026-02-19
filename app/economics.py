from dataclasses import dataclass
from typing import Optional

@dataclass(frozen=True)
class EconomicsAssumptions:
    ebay_fee_rate: float
    risk_buffer_rate: float
    default_shipping_usd: float

def expected_profit_buy_live_sell_at_sold_median(
    live_price: float,
    sold_median: float,
    assumptions: EconomicsAssumptions,
    live_shipping: Optional[float] = None,
) -> dict:
    ship_buy = assumptions.default_shipping_usd if live_shipping is None else float(live_shipping)

    buy_total = float(live_price) + ship_buy

    gross = float(sold_median)
    ebay_fee = gross * assumptions.ebay_fee_rate
    risk = gross * assumptions.risk_buffer_rate

    net_sale = gross - ebay_fee - risk
    profit = net_sale - buy_total
    roi = None if buy_total <= 0 else profit / buy_total

    return {
        "live_price": float(live_price),
        "live_shipping": ship_buy,
        "buy_total": buy_total,
        "sold_median": gross,
        "ebay_fee": ebay_fee,
        "risk_buffer": risk,
        "net_sale": net_sale,
        "profit": profit,
        "roi": roi,
    }
