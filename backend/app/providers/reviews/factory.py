from app.config import get_settings
from app.providers.reviews.base import ReviewsProvider
from app.providers.reviews.google_places import GooglePlacesProvider
from app.providers.reviews.mock import MockReviewsProvider
from app.providers.reviews.reddit import RedditProvider


def get_reviews_providers() -> list[ReviewsProvider]:
    """All configured review sources (the agent merges them)."""
    settings = get_settings()
    if settings.demo_mode:
        return [MockReviewsProvider()]
    providers: list[ReviewsProvider] = []
    if settings.google_places_api_key:
        providers.append(GooglePlacesProvider(settings.google_places_api_key))
    if settings.reddit_client_id and settings.reddit_client_secret:
        providers.append(RedditProvider(settings.reddit_client_id, settings.reddit_client_secret))
    return providers or [MockReviewsProvider()]
