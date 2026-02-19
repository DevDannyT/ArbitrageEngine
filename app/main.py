from fastapi import FastAPI, Request, Query
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.config import settings
from app.cache import TTLCache
from app.providers.ebay import EbayClient
from app.matching import build_market_query, score_listing_against_query
from app.statistics import summarize_prices
from app.economics import EconomicsAssumptions, expected_profit_buy_live_sell_at_sold_median
from app.scoring import rank_opportunities

app = FastAPI(title="CardCompare Flip Radar (eBay-only)")

app.mount("/static", StaticFiles(directory="app/static"), name="static")
templates = Jinja2Templates(directory="app/templates")

cache = TTLCache(settings.cache_ttl_seconds)

ebay = EbayClient(
    client_id=settings.ebay_client_id,
    client_secret=settings.ebay_client_secret,
    marketplace_id=settings.ebay_marketplace_id,
    cache=cache,
)

econ = EconomicsAssumptions(
    ebay_fee_rate=settings.ebay_fee_rate,
    risk_buffer_rate=settings.risk_buffer_rate,
    default_shipping_usd=settings.default_shipping_usd,
)

@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/health")
async def health():
    return {"status": "ok"}

@app.get("/results", response_class=HTMLResponse)
async def results_page(
    request: Request,
    game: str = Query("pokemon"),
    q: str = Query(...),
):
    market_query = build_market_query(game, q)

    # --- Fetch live listings ---
    live_key = f"ebay:live:{market_query}".lower()
    live = cache.get(live_key)
    if not live:
        live = await ebay.search(market_query, limit=settings.default_ebay_limit_live, sold=False)
        cache.set(live_key, live)

    # --- Fetch sold comps ---
    sold_key = f"ebay:sold:{market_query}".lower()
    sold = cache.get(sold_key)
    if not sold:
        sold = await ebay.search(market_query, limit=settings.default_ebay_limit_sold, sold=True)
        cache.set(sold_key, sold)

    # --- Score + filter sold items for clean comps ---
    sold_prices = []
    sold_scored = []
    for it in sold.get("items", []):
        if not it.get("price_value"):
            continue
        m = score_listing_against_query(q, it)
        if m["confidence"] < settings.min_confidence:
            continue
        sold_prices.append(float(it["price_value"]))
        sold_scored.append({"item": it, "match": m})

    sold_stats = summarize_prices(sold_prices)
    sold_median = sold_stats.get("median")

    opportunities = []
    if sold_median:
        for it in live.get("items", []):
            price = it.get("price_value")
            if not price:
                continue

            m = score_listing_against_query(q, it)
            conf = m["confidence"]
            if conf < settings.min_confidence:
                continue

            ship = it.get("shipping_value")
            total = float(price) + (settings.default_shipping_usd if ship is None else float(ship))

            discount = 1.0 - (total / float(sold_median))
            if discount < settings.min_discount:
                continue

            econ_out = expected_profit_buy_live_sell_at_sold_median(
                live_price=float(price),
                sold_median=float(sold_median),
                assumptions=econ,
                live_shipping=ship,
            )

            if econ_out["profit"] < settings.min_profit_usd:
                continue

            opportunities.append({
                "item": it,
                "match": m,
                "discount": discount,
                "economics": econ_out,
            })

    ranked = rank_opportunities(opportunities)

    ctx = {
        "request": request,
        "game": game,
        "q": q,
        "market_query": market_query,
        "sold_stats": sold_stats,
        "sold_count_used": len(sold_prices),
        "ranked": ranked,
        "min_confidence": settings.min_confidence,
        "min_discount": settings.min_discount,
        "min_profit_usd": settings.min_profit_usd,
    }
    return templates.TemplateResponse("results.html", ctx)
