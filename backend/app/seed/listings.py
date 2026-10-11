"""Deterministic generator for 150 realistic South Bay demo listings."""

import random
from datetime import UTC, datetime, timedelta

from app.agents.contracts import Fee, ListingModel
from app.seed.buildings import BUILDINGS

SEED = 42

_CITY_BASE_RENT = {
    # (1-bed base rent, $/sqft hint)
    "Sunnyvale": 2750,
    "Santa Clara": 2600,
    "Mountain View": 2950,
    "Cupertino": 2850,
    "San Jose": 2350,
}

_CITY_CENTERS = {
    "Sunnyvale": (37.3688, -122.0363),
    "Santa Clara": (37.3541, -121.9552),
    "Mountain View": (37.3861, -122.0839),
    "Cupertino": (37.3230, -122.0322),
    "San Jose": (37.3382, -121.8863),
}

_STREETS = {
    "Sunnyvale": [
        "S Mary Ave",
        "E Fremont Ave",
        "Hollenbeck Ave",
        "S Wolfe Rd",
        "W McKinley Ave",
        "Iowa Ave",
    ],
    "Santa Clara": [
        "Benton St",
        "Homestead Rd",
        "Monroe St",
        "Pomeroy Ave",
        "Kiely Blvd",
        "Warburton Ave",
    ],
    "Mountain View": [
        "California St",
        "Latham St",
        "Escuela Ave",
        "Rengstorff Ave",
        "Middlefield Rd",
    ],
    "Cupertino": ["Stelling Rd", "Blaney Ave", "Bollinger Rd", "Rodrigues Ave", "Pacifica Dr"],
    "San Jose": [
        "Meridian Ave",
        "Lincoln Ave",
        "The Alameda",
        "Park Ave",
        "S Bascom Ave",
        "Curtner Ave",
    ],
}

_AMENITY_POOL = [
    "in-unit laundry",
    "parking",
    "garage parking",
    "pool",
    "gym",
    "dishwasher",
    "air conditioning",
    "balcony",
    "dog friendly",
    "cat friendly",
    "ev charging",
    "stainless appliances",
    "hardwood floors",
    "rooftop deck",
    "bike storage",
    "package lockers",
    "courtyard",
    "smart lock",
]

_MANAGERS = [
    "Bayline Property Mgmt",
    "Golden State Residential",
    "Peninsula Homes LLC",
    "Private owner",
    "Sequoia Property Group",
    "Westbrook Realty",
]

_UNIT_MIX: list[tuple[float, float, int, int]] = [
    # (beds, baths, sqft_lo, sqft_hi)
    (0.0, 1.0, 420, 560),
    (1.0, 1.0, 560, 780),
    (2.0, 1.0, 800, 950),
    (2.0, 2.0, 900, 1180),
    (3.0, 2.0, 1150, 1500),
]


def _rent_for(rng: random.Random, city: str, beds: float, baths: float, sqft: int) -> int:
    base = _CITY_BASE_RENT[city]
    multiplier = {0.0: 0.78, 1.0: 1.0, 2.0: 1.32, 3.0: 1.68}[beds]
    bath_bump = 1.0 + (baths - 1.0) * 0.05
    sqft_adj = 1.0 + (sqft - 750) / 7500
    noise = rng.uniform(0.9, 1.12)
    return int(round(base * multiplier * bath_bump * sqft_adj * noise / 25) * 25)


def generate_listings() -> list[ListingModel]:
    rng = random.Random(SEED)
    now = datetime(2026, 10, 1, tzinfo=UTC)
    listings: list[ListingModel] = []

    def make(
        city: str,
        address: str,
        lat: float,
        lng: float,
        building_name: str | None,
        manager: str,
        i: int,
    ) -> ListingModel:
        beds, baths, sqft_lo, sqft_hi = rng.choice(_UNIT_MIX)
        sqft = rng.randrange(sqft_lo, sqft_hi, 10)
        rent = _rent_for(rng, city, beds, baths, sqft)
        amenities = rng.sample(_AMENITY_POOL, rng.randint(3, 8))
        if building_name:  # professionally managed buildings market pet policies
            if rng.random() < 0.7 and "dog friendly" not in amenities:
                amenities.append("dog friendly")
            if "package lockers" not in amenities and rng.random() < 0.4:
                amenities.append("package lockers")
        fees: list[Fee] = []
        if rng.random() < 0.65:
            fees.append(
                Fee(
                    name="parking",
                    amount=rng.choice([0, 50, 75, 100, 125]),
                    period="monthly",
                    mandatory=False,
                )
            )
        if "dog friendly" in amenities or "cat friendly" in amenities:
            fees.append(
                Fee(
                    name="pet rent",
                    amount=rng.choice([35, 50, 75]),
                    period="monthly",
                    mandatory=False,
                )
            )
        if rng.random() < 0.5:
            fees.append(
                Fee(
                    name="utilities (flat RUBS)",
                    amount=rng.choice([60, 85, 110]),
                    period="monthly",
                    mandatory=True,
                )
            )
        if rng.random() < 0.45:
            fees.append(
                Fee(
                    name="admin fee",
                    amount=rng.choice([150, 250, 350]),
                    period="one_time",
                    mandatory=True,
                )
            )
        listed_days_ago = rng.randint(0, 55)
        available = now + timedelta(days=rng.randint(3, 60))
        deposit = rent if rng.random() < 0.6 else int(rent * rng.choice([0.5, 1.5, 2.0]))
        lid = f"demo{i:04d}"
        return ListingModel(
            id=lid,
            source="demo",
            url=f"https://demo.leaselens.dev/listings/{lid}",
            address=address,
            city=city,
            lat=round(lat, 5),
            lng=round(lng, 5),
            rent=rent,
            deposit=deposit,
            fees=fees,
            beds=beds,
            baths=baths,
            sqft=sqft,
            amenities=sorted(amenities),
            photos=[f"https://picsum.photos/seed/leaselens-{lid}-{k}/640/420" for k in range(3)],
            available_date=available.date().isoformat(),
            landlord=manager,
            building_name=building_name,
            listed_at=now - timedelta(days=listed_days_ago),
        )

    i = 0
    # ~60 units inside the 15 named buildings (4 units each)
    for building in BUILDINGS:
        for _unit in range(4):
            jitter = (rng.uniform(-0.0004, 0.0004), rng.uniform(-0.0004, 0.0004))
            address = f"{building.address.split(',')[0]} Unit {rng.choice(['A', 'B', 'C'])}{rng.randint(101, 428)}, {building.city}, CA"
            listings.append(
                make(
                    building.city,
                    address,
                    building.lat + jitter[0],
                    building.lng + jitter[1],
                    building.name,
                    building.manager,
                    i,
                )
            )
            i += 1

    # ~90 scattered small-landlord listings
    cities = list(_CITY_BASE_RENT)
    while len(listings) < 150:
        city = cities[i % len(cities)]
        clat, clng = _CITY_CENTERS[city]
        street = rng.choice(_STREETS[city])
        number = rng.randrange(100, 2400)
        lat = clat + rng.uniform(-0.018, 0.018)
        lng = clng + rng.uniform(-0.022, 0.022)
        listings.append(
            make(city, f"{number} {street}, {city}, CA", lat, lng, None, rng.choice(_MANAGERS), i)
        )
        i += 1

    # One deliberate cross-source duplicate (same unit, slightly different
    # address formatting) so the Scout's dedupe has something to catch.
    dupe_src = listings[3]
    dupe = dupe_src.model_copy(deep=True)
    dupe.id = "demo9999"
    dupe.source = "demo"
    dupe.url = "https://demo.leaselens.dev/listings/demo9999"
    dupe.address = dupe_src.address.replace("Unit ", "#").replace(", CA", ", CA 94086")
    dupe.rent = dupe_src.rent + 10
    listings.append(dupe)

    return listings
