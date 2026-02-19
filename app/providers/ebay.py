from __future__ import annotations
from typing import Any, Dict, List, Optional
import base64
import httpx

EBAY_TOKEN_URL = "https://api.ebay.com/identity/v1/oauth2/token"
EBAY_BROWSE_SEARCH = "https://api.ebay.com/buy/browse/v1/item_summary/search"

class EbayClient:
    def __init__(self, client_id: str, client_secret: str, marketplace_id: str, cache):
        self.client_id = client_id
        self.client_secret = client_secret
        self.marketplace_id = marketplace_id
        self.cache = cache

    def _basic_auth_header(self) -> str:
        raw = f"{self.client_id}:{self.client_secret}".encode("utf-8")
        return base64.b64encode(raw).decode("utf-8")

    async def _get_access_token(self) -> str:
        cache_key = "ebay:token"
        cached = self.cache.get(cache_key)
        if cached:
            return cached

        if not self.client_id or not self.client_secret:
            raise RuntimeError("Missing eBay creds. Set EBAY_CLIENT_ID and EBAY_CLIENT_SECRET in .env")

        headers = {
            "Authorization": f"Basic {self._basic_auth_header()}",
            "Content-Type": "application/x-www-form-urlencoded",
        }
        data = {"grant_type": "client_credentials", "scope": "https://api.ebay.com/oauth/api_scope"}

        async with httpx.AsyncClient(timeout=20) as client:
            resp = await client.post(EBAY_TOKEN_URL, headers=headers, data=data)
            resp.raise_for_status()
            payload = resp.json()

        token = payload["access_token"]
        self.cache.set(cache_key, token)
        return token

    async def search(self, q: str, limit: int = 30, sold: bool = False) -> Dict[str, Any]:
        """
        Uses eBay Browse API search.
        sold=False => live listings
        sold=True  => sold items (if your eBay access supports it via filter=soldItems:true)
        """
        token = await self._get_access_token()

        headers = {
            "Authorization": f"Bearer {token}",
            "X-EBAY-C-MARKETPLACE-ID": self.marketplace_id,
        }

        filters: List[str] = []
        # these are safe defaults; tweak later
        filters.append("deliveryCountry:US")
        if sold:
            filters.append("soldItems:true")

        params = {
            "q": q,
            "limit": min(limit, 50),
        }
        if filters:
            params["filter"] = ",".join(filters)

        async with httpx.AsyncClient(timeout=20) as client:
            resp = await client.get(EBAY_BROWSE_SEARCH, headers=headers, params=params)
            resp.raise_for_status()
            data = resp.json()

        items: List[Dict[str, Any]] = []
        for it in data.get("itemSummaries", [])[:limit]:
            price = it.get("price") or {}
            ship_obj = None
            if it.get("shippingOptions"):
                ship_obj = (it.get("shippingOptions") or [{}])[0].get("shippingCost")

            price_value = None
            ship_value = None
            try:
                price_value = float(price.get("value")) if price.get("value") is not None else None
            except Exception:
                price_value = None

            if ship_obj:
                try:
                    ship_value = float(ship_obj.get("value")) if ship_obj.get("value") is not None else None
                except Exception:
                    ship_value = None

            items.append({
                "title": it.get("title") or "",
                "itemWebUrl": it.get("itemWebUrl"),
                "price_value": price_value,
                "currency": price.get("currency"),
                "image": (it.get("image") or {}).get("imageUrl"),
                "condition": it.get("condition"),
                "seller": (it.get("seller") or {}).get("username"),
                "shipping_value": ship_value,
            })

        return {"source": "ebay", "query": q, "sold": sold, "items": items}
