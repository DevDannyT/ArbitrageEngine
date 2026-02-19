from __future__ import annotations
from typing import Any, Dict, List
import base64
import httpx

TCG_AUTH_URL = "https://api.tcgplayer.com/token"
TCG_API_BASE = "https://api.tcgplayer.com"

DEFAULT_CATEGORY_IDS = {
    "mtg": 1,
    "pokemon": 3,
}

class TCGPlayerClient:
    def __init__(self, public_key: str, private_key: str, cache):
        self.public_key = public_key
        self.private_key = private_key
        self.cache = cache

    def _basic_auth_header(self) -> str:
        raw = f"{self.public_key}:{self.private_key}".encode("utf-8")
        return base64.b64encode(raw).decode("utf-8")

    async def _get_access_token(self) -> str:
        cache_key = "tcg:token"
        cached = self.cache.get(cache_key)
        if cached:
            return cached

        if not self.public_key or not self.private_key:
            raise RuntimeError("Missing TCGplayer keys. Set TCGPLAYER_PUBLIC_KEY and TCGPLAYER_PRIVATE_KEY in .env")

        headers = {
            "Authorization": f"Basic {self._basic_auth_header()}",
            "Content-Type": "application/x-www-form-urlencoded",
        }
        data = {"grant_type": "client_credentials"}

        async with httpx.AsyncClient(timeout=20) as client:
            resp = await client.post(TCG_AUTH_URL, headers=headers, data=data)
            resp.raise_for_status()
            payload = resp.json()

        token = payload["access_token"]
        self.cache.set(cache_key, token)
        return token

    async def search_products(self, game: str, q: str, limit: int = 20) -> List[Dict[str, Any]]:
        token = await self._get_access_token()
        category_id = DEFAULT_CATEGORY_IDS.get(game.lower())
        if not category_id:
            raise ValueError("game must be 'pokemon' or 'mtg'")

        url = f"{TCG_API_BASE}/catalog/products"
        headers = {"Authorization": f"bearer {token}"}
        params = {
            "categoryId": category_id,
            "productName": q,
            "getExtendedFields": "true",
            "pageSize": min(limit, 50),
        }

        async with httpx.AsyncClient(timeout=20) as client:
            resp = await client.get(url, headers=headers, params=params)
            resp.raise_for_status()
            data = resp.json()

        results: List[Dict[str, Any]] = []
        for item in data.get("results", []):
            ext = {f.get("name"): f.get("value") for f in item.get("extendedData", []) if isinstance(f, dict)}
            results.append({
                "source": "tcgplayer",
                "game": game.lower(),
                "productId": item.get("productId"),
                "name": item.get("name"),
                "imageUrl": item.get("imageUrl"),
                "set": ext.get("Set Name") or ext.get("Set") or ext.get("Expansion"),
                "number": ext.get("Number") or ext.get("Card Number"),
                "rarity": ext.get("Rarity"),
                "printedType": ext.get("Printed Type") or ext.get("Card Type"),
            })
        return results

    async def get_prices(self, product_id: int) -> Dict[str, Any]:
        token = await self._get_access_token()
        url = f"{TCG_API_BASE}/pricing/product/{product_id}"
        headers = {"Authorization": f"bearer {token}"}

        async with httpx.AsyncClient(timeout=20) as client:
            resp = await client.get(url, headers=headers)
            resp.raise_for_status()
            data = resp.json()

        rows = data.get("results", [])
        prices = []
        for r in rows:
            prices.append({
                "subTypeName": r.get("subTypeName"),
                "marketPrice": r.get("marketPrice"),
                "lowPrice": r.get("lowPrice"),
                "midPrice": r.get("midPrice"),
                "highPrice": r.get("highPrice"),
                "directLowPrice": r.get("directLowPrice"),
            })

        return {"source": "tcgplayer", "productId": product_id, "prices": prices}
