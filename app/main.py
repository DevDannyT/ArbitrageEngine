from fastapi import FastAPI, Request, Query
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.config import settings
from app.cache import TTLCache
from app.providers.tcgplayer import TCGPlayerClient
from app.providers.ebay import EbayClient
from app.matching import build_ebay_query, score_ebay_listing
from app.economics import EconomicsAssumptions, expected_profit_buy_ebay_sell_tcg
from app.scoring import rank_opportunities

app = FastAPI(title="CardCompare Flip Radar")

app.mount("/static", StaticFiles(directory="app/static"), name="static")
templates = Jinja2Templates(directory="app/templates")

cache = TTLCache(settings.cache_ttl_seconds)

tcg = TCGPlayerClient(
    public_key=settings.tcgplayer_public_key,
    private_key=settings.tcgplayer_private_key,
    cache=cache,
)

ebay = EbayClient(
    client_id=settings.ebay_client_id,
    client_secret=settings.ebay_client_secret,
    marketplace_id=settings.ebay_marketplace_id,
    cache=cache,
)

econ = EconomicsAssumptions(
    ebay_fee_rate=settings.ebay_fee_rate,
    tcg_seller_fee_rate=settings.tcg_seller_fee_rate,
    risk_buffer_rate=settings.risk_buffer_rate,
    default_shipping_usd=settings.default_shipping_usd,
)


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.get("/api/search")
async def api_search(game: str = Query(...), q: str = Query(...)):
    # Cache search results briefly
    key = f"search:{game}:{q}".lower()
    cached = cache.get(key)
    if cached:
        return JSONResponse(cached)

    results = await tcg.search_products(game=game, q=q, limit=20)
    cache.set(key, results)
    return JSONResponse(results)


@app.get("/results", response_class=HTMLResponse)
async def results_page(
    request: Request,
    game: str = Query(...),
    product_id: int = Query(...),
):
    # 1) get selected card basics
    card_key = f"card:{game}:{product_id}"
    card = cache.get(card_key)
    if not card:
        # lightweight re-fetch: search by product ID isn't in our client, so we rely on prior search selection
        # If user hits URL directly, we can still show basic info:
        card = {"game": game, "productId": product_id, "name": f"Product {product_id}"}

    # 2) TCGplayer prices
    price_key = f"tcgprice:{product_id}"
    tcg_prices = cache.get(price_key)
    if not tcg_prices:
        tcg_prices = await tcg.get_prices(product_id)
        cache.set(price_key, tcg_prices)

    # choose a sell price baseline: prefer "Normal" market price, else first market price
    sell_price = None
    for row in tcg_prices.get("prices", []):
        if (row.get("subTypeName") or "").lower() == "normal" and row.get("marketPrice"):
            sell_price = row["marketPrice"]
            break
    if sell_price is None:
        for row in tcg_prices.get("prices", []):
            if row.get("marketPrice"):
                sell_price = row["marketPrice"]
                break

    # 3) Build eBay query + search
    query_str = build_ebay_query(card)
    ebay_key = f"ebay:{query_str}".lower()
    ebay_result = cache.get(ebay_key)
    if not ebay_result:
        ebay_result = await ebay.search(query_str, limit=settings.default_ebay_limit)
        cache.set(ebay_key, ebay_result)

    # 4) Score listings for match/confidence, compute opportunities
    opportunities = []
    if sell_price:
        for it in ebay_result.get("items", []):
            score = score_ebay_listing(card, it)
            conf = score["confidence"]
            if conf < settings.min_confidence:
                continue

            buy_price = it.get("price_value")
            if not buy_price:
                continue

            ship = it.get("shipping_value")
            prof = expected_profit_buy_ebay_sell_tcg(
                ebay_buy_price=buy_price,
                tcg_sell_price=sell_price,
                assumptions=econ,
                shipping_cost=ship,
            )

            if prof["roi"] is None or prof["roi"] < settings.min_roi:
                continue

            opportunities.append({
                "item": it,
                "match": score,
                "economics": prof,
            })

    ranked = rank_opportunities(opportunities)

    ctx = {
        "request": request,
        "card": card,
        "tcg_prices": tcg_prices,
        "sell_price": sell_price,
        "ebay_query": query_str,
        "ranked": ranked,
        "min_confidence": settings.min_confidence,
        "min_roi": settings.min_roi,
    }
    return templates.TemplateResponse("results.html", ctx)
