from app.config import get_settings
from app.providers.commute.base import CommuteProvider
from app.providers.commute.mock import MockCommuteProvider
from app.providers.commute.openrouteservice import OpenRouteServiceProvider


def get_commute_provider() -> CommuteProvider:
    settings = get_settings()
    if not settings.demo_mode and settings.openrouteservice_api_key:
        return OpenRouteServiceProvider(settings.openrouteservice_api_key)
    return MockCommuteProvider()
