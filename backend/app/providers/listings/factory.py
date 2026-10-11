from app.config import get_settings
from app.providers.listings.base import ListingsProvider
from app.providers.listings.mock import MockListingsProvider
from app.providers.listings.rentcast import RentCastProvider


def get_listings_provider() -> ListingsProvider:
    settings = get_settings()
    if not settings.demo_mode and settings.rentcast_api_key:
        return RentCastProvider(settings.rentcast_api_key)
    return MockListingsProvider()
