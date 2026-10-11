"""Review/post fixtures: ~40+ docs across the 15 demo buildings, with themed
complaints, recency spikes, and one suspicious 5-star burst."""

import random
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from app.seed.buildings import BUILDINGS

SEED = 1337
_NOW = datetime(2026, 10, 1, tzinfo=UTC)


@dataclass
class ReviewFixture:
    building_key: str
    source_type: str  # google | reddit
    author: str
    rating: float | None
    text: str
    posted_at: datetime
    external_id: str
    url: str


_THEME_TEXTS = {
    "pests": [
        (
            "Saw roaches in the kitchen twice this month. Pest control comes but they keep coming back.",
            2,
        ),
        (
            "Management finally sprayed for the cockroach problem but the mice in the garage are still around.",
            2,
        ),
        ("Roaches. In 2026. For this rent. Unbelievable.", 1),
    ],
    "noise": [
        (
            "Walls are paper thin — I can hear my neighbor's alarm every morning. Freeway noise is constant on the east side.",
            2,
        ),
        (
            "Upstairs neighbors sound like a bowling league. Complained to the office, nothing changed.",
            2,
        ),
        ("Lovely courtyard but the train horn at 5am takes getting used to.", 3),
    ],
    "maintenance": [
        ("Work orders take 3+ weeks. My dishwasher has been broken since July.", 2),
        (
            "Maintenance staff are nice but clearly understaffed; the elevator was out for a month.",
            2,
        ),
        ("AC died during the heat wave and it took 10 days to get a repair visit.", 1),
    ],
    "management": [
        (
            "Office never answers email. They charged me a $200 'cleaning fee' at move-out with zero documentation.",
            1,
        ),
        (
            "Lease renewal came with a 9% increase and they wouldn't negotiate at all. Deposit took 5 weeks to come back.",
            2,
        ),
        ("New front office staff are rude and lose packages. Corporate doesn't respond.", 1),
    ],
    "safety": [
        ("Two car break-ins in the garage last month. Gate has been broken for weeks.", 1),
        ("Someone tailgated into the lobby and stole bikes from the storage room.", 2),
        ("Generally felt safe, but the parking lot lighting is really dim.", 3),
    ],
    "parking": [
        (
            "Guest parking is a joke — 6 spots for 200 units. They tow aggressively, $450 to get your car back.",
            2,
        ),
        ("Assigned spot is so tight I've scraped my door twice. Second car costs $125/mo.", 2),
    ],
    "package_theft": [
        (
            "Packages get stolen from the lobby constantly. Amazon won't even deliver here anymore without a locker.",
            1,
        ),
        ("Third stolen package this quarter. Cameras 'don't cover that corner' apparently.", 1),
    ],
    "water_heat": [
        ("No hot water on weekend mornings, radiators clank all night in winter.", 2),
        (
            "Water was shut off 4 times this summer for 'emergency repairs'. Heating bill is wild because the windows leak.",
            2,
        ),
    ],
}

_POSITIVE_TEXTS = [
    ("Quiet building, responsive maintenance, and the courtyard is lovely in spring.", 5),
    ("Lived here 2 years — rent increases were reasonable and the gym is actually good.", 4),
    ("Great location near Caltrain, management fixed my sink the same week I asked.", 5),
    ("Solid value for the area. Thin walls but considerate neighbors.", 4),
    ("Move-in was smooth and the unit matched the photos.", 4),
]

_FAKE_BURST_TEXTS = [
    "Absolutely amazing luxury living experience! Best management team ever!!!",
    "5 stars! The leasing staff is incredible and the amenities are world class!",
    "Best apartment in Sunnyvale, hands down. Everyone should live here!",
    "Incredible value, stunning units, perfect management. 10/10!",
    "The BEST community! Maintenance is instant and the pool is gorgeous!!",
    "Flawless experience from tour to move-in! Highly recommend to everyone!",
]

_REDDIT_AUTHORS = [
    "bay_renter_22",
    "southbay_sam",
    "caltrain_commuter",
    "apt_hunter_sj",
    "nimby_neighbor",
    "sunnyvale_sarah",
]
_GOOGLE_AUTHORS = [
    "Priya K.",
    "Daniel M.",
    "Alex T.",
    "Morgan W.",
    "Chris B.",
    "Jamie L.",
    "Taylor R.",
]


def generate_reviews() -> list[ReviewFixture]:
    rng = random.Random(SEED)
    fixtures: list[ReviewFixture] = []
    counter = 0

    def add(building_key: str, text: str, rating: int | None, days_ago: int, source: str) -> None:
        nonlocal counter
        counter += 1
        author = rng.choice(_REDDIT_AUTHORS if source == "reddit" else _GOOGLE_AUTHORS)
        fixtures.append(
            ReviewFixture(
                building_key=building_key,
                source_type=source,
                author=author,
                rating=float(rating) if source == "google" and rating else None,
                text=text,
                posted_at=_NOW - timedelta(days=days_ago),
                external_id=f"demo-review-{counter:03d}",
                url=(
                    f"https://maps.google.com/?cid=demo-{building_key}-{counter}"
                    if source == "google"
                    else f"https://www.reddit.com/r/bayarea/comments/demo_{building_key}_{counter}"
                ),
            )
        )

    for building in BUILDINGS:
        profile = building.profile
        if profile == "clean":
            for text, rating in rng.sample(_POSITIVE_TEXTS, 2):
                add(
                    building.key,
                    text,
                    rating,
                    rng.randint(30, 600),
                    rng.choice(["google", "reddit"]),
                )
        elif profile == "fake_burst":
            # Suspicious: six 5-star reviews within a 10-day window, plus two
            # older negative ones telling a different story.
            base_day = rng.randint(20, 30)
            for k, text in enumerate(_FAKE_BURST_TEXTS):
                add(building.key, text, 5, base_day + (k % 10), "google")
            add(
                building.key,
                "Management asked residents for 5-star reviews in exchange for a gift card. The garage gate has been broken since March.",
                2,
                150,
                "reddit",
            )
            add(building.key, _THEME_TEXTS["maintenance"][0][0], 2, 220, "google")
        elif profile == "new_management_spike":
            # Older reviews fine; complaints spike in the last 6 months.
            for text, rating in rng.sample(_POSITIVE_TEXTS, 2):
                add(building.key, text, rating, rng.randint(400, 800), "google")
            spike_texts = _THEME_TEXTS["management"] + [_THEME_TEXTS["maintenance"][1]]
            for text, rating in spike_texts:
                add(
                    building.key,
                    f"{text} It all went downhill when Yardstone PM took over this spring.",
                    rating,
                    rng.randint(10, 160),
                    rng.choice(["google", "reddit"]),
                )
        else:
            theme_pool = _THEME_TEXTS[profile]
            for text, rating in theme_pool:
                add(
                    building.key,
                    text,
                    rating,
                    rng.randint(20, 400),
                    rng.choice(["google", "reddit"]),
                )
            text, rating = rng.choice(_POSITIVE_TEXTS)
            add(building.key, text, rating, rng.randint(30, 500), "google")

    return fixtures
