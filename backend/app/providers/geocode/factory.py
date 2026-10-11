from app.config import get_settings
from app.providers.geocode.base import Geocoder
from app.providers.geocode.mock import MockGeocoder
from app.providers.geocode.nominatim import NominatimGeocoder


def get_geocoder() -> Geocoder:
    settings = get_settings()
    if not settings.demo_mode:
        return NominatimGeocoder()
    return MockGeocoder()
