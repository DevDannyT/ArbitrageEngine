from dataclasses import dataclass
from typing import Optional

@dataclass(frozen=True)
class EconomicsAssumptions:
    ebay_fee_rate: float
    tcg_seller_fee_rate: float
    risk_buffer_rate: float
    default_shipping_usd: float

def expected_profit_buy_ebay_sell_tcg(
    ebay_buy_price: float,
    tcg_sell_price: float,
    assumptions: EconomicsAssumptions,
    shipping_cost: Optional[float] = None,
) -> dict:
    ship = assumptions.default_shipping_usd if shipping_cost is None else float(shipping_cost)

    cost_basis = float(ebay_buy_price) + ship

    gross = float(tcg_sell_price)
    tcg_fee = gross * assumptions.tcg_seller_fee_rate
    risk_buffer = gross * assumptions.risk_buffer_rate

    net_sale = gross - tcg_fee - risk_buffer
    profit = net_sale - cost_basis
    roi = None if cost_basis <= 0 else profit / cost_basis

    return {
        "buy_price": float(ebay_buy_price),
        "shipping": ship,
        "cost_basis": cost_basis,
        "sell_price": gross,
        "tcg_fee": tcg_fee,
        "risk_buffer": risk_buffer,
        "net_sale": net_sale,
        "profit": profit,
        "roi": roi,
    }
