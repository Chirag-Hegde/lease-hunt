from app.config import get_settings
from app.providers.listings.base import ListingsProvider
from app.providers.listings.mock import MockListingsProvider
from app.providers.listings.rentcast import RentCastProvider


def get_listings_provider() -> ListingsProvider:
    # A RentCast key activates live US-wide search even in demo mode,
    # mirroring the LLM provider hybrid (mock everything else, real listings).
    settings = get_settings()
    if settings.rentcast_api_key:
        return RentCastProvider(settings.rentcast_api_key)
    return MockListingsProvider()
