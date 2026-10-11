"""DB row ↔ contract model mappers."""

from typing import Any

from app.agents.contracts import Fee, ListingModel
from app.db import models
from app.services.geo import normalize_address


def listing_row_to_model(row: models.Listing) -> ListingModel:
    return ListingModel(
        id=row.id,
        source=row.source,
        url=row.url,
        address=row.address,
        city=row.city,
        lat=row.lat,
        lng=row.lng,
        rent=row.rent,
        deposit=row.deposit,
        fees=[Fee.model_validate(f) for f in row.fees],
        beds=row.beds,
        baths=row.baths,
        sqft=row.sqft,
        amenities=list(row.amenities),
        photos=list(row.photos),
        available_date=row.available_date,
        landlord=row.landlord,
        building_name=row.building_name,
        raw_text=row.raw_text,
        listed_at=row.listed_at,
    )


def listing_model_to_row(listing: ListingModel) -> models.Listing:
    return models.Listing(
        id=listing.id,
        source=listing.source,
        url=listing.url,
        address=listing.address,
        normalized_address=normalize_address(listing.address),
        city=listing.city,
        lat=listing.lat,
        lng=listing.lng,
        rent=listing.rent,
        deposit=listing.deposit,
        fees=[f.model_dump(mode="json") for f in listing.fees],
        beds=listing.beds,
        baths=listing.baths,
        sqft=listing.sqft,
        amenities=list(listing.amenities),
        photos=list(listing.photos),
        available_date=listing.available_date,
        landlord=listing.landlord,
        building_name=listing.building_name,
        raw_text=listing.raw_text,
        listed_at=listing.listed_at,
    )


def agent_result_payload(result: Any) -> dict[str, Any]:
    """Serialize an AgentResult for a JSON column."""
    payload: dict[str, Any] = result.model_dump(mode="json")
    return payload
