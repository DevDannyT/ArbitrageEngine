import os
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()

def _f(name: str, default: float) -> float:
    try:
        return float(os.getenv(name, str(default)))
    except Exception:
        return default

def _i(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, str(default)))
    except Exception:
        return default

@dataclass(frozen=True)
class Settings:
    tcgplayer_public_key: str = os.getenv("TCGPLAYER_PUBLIC_KEY", "")
    tcgplayer_private_key: str = os.getenv("TCGPLAYER_PRIVATE_KEY", "")

    ebay_client_id: str = os.getenv("EBAY_CLIENT_ID", "")
    ebay_client_secret: str = os.getenv("EBAY_CLIENT_SECRET", "")
    ebay_marketplace_id: str = os.getenv("EBAY_MARKETPLACE_ID", "EBAY_US")

    cache_ttl_seconds: int = _i("CACHE_TTL_SECONDS", 1800)
    default_ebay_limit: int = _i("DEFAULT_EBAY_LIMIT", 30)

    ebay_fee_rate: float = _f("EBAY_FEE_RATE", 0.1325)
    tcg_seller_fee_rate: float = _f("TCG_SELLER_FEE_RATE", 0.105)
    risk_buffer_rate: float = _f("RISK_BUFFER_RATE", 0.07)
    default_shipping_usd: float = _f("DEFAULT_SHIPPING_USD", 4.50)

    min_confidence: float = _f("MIN_CONFIDENCE", 0.55)
    min_roi: float = _f("MIN_ROI", 0.10)

settings = Settings()
