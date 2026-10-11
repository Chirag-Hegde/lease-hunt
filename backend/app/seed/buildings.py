"""The 15 named demo buildings. Review fixtures and some listings attach to
these; building_key = slug of the name."""

from dataclasses import dataclass


@dataclass(frozen=True)
class DemoBuilding:
    key: str
    name: str
    city: str
    address: str
    lat: float
    lng: float
    manager: str
    # Review personality (used by the review seed generator)
    profile: str  # clean | pests | noise | maintenance | management | parking | safety | package_theft | water_heat | fake_burst | new_management_spike


BUILDINGS: list[DemoBuilding] = [
    DemoBuilding(
        "cedar-grove",
        "Cedar Grove Apartments",
        "Sunnyvale",
        "1044 Cedar Grove Ln, Sunnyvale, CA 94086",
        37.3762,
        -122.0248,
        "Greystar",
        "clean",
    ),
    DemoBuilding(
        "marlow-commons",
        "Marlow Commons",
        "Sunnyvale",
        "550 S Fair Oaks Ave, Sunnyvale, CA 94086",
        37.3641,
        -122.0219,
        "Marlow Residential",
        "pests",
    ),
    DemoBuilding(
        "orchard-terrace",
        "Orchard Terrace",
        "Sunnyvale",
        "212 W Washington Ave, Sunnyvale, CA 94086",
        37.3791,
        -122.0334,
        "Orchard PM Group",
        "noise",
    ),
    DemoBuilding(
        "aria-station",
        "Aria at the Station",
        "Sunnyvale",
        "121 Evelyn Ave, Sunnyvale, CA 94086",
        37.3775,
        -122.0297,
        "Aria Living",
        "fake_burst",
    ),
    DemoBuilding(
        "juniper-flats",
        "Juniper Flats",
        "Santa Clara",
        "2805 Bowers Ave, Santa Clara, CA 95051",
        37.3703,
        -121.9814,
        "FPI Management",
        "maintenance",
    ),
    DemoBuilding(
        "mission-pointe",
        "Mission Pointe Villas",
        "Santa Clara",
        "1700 Halford Ave, Santa Clara, CA 95051",
        37.3498,
        -121.9985,
        "Essex Property",
        "clean",
    ),
    DemoBuilding(
        "coleman-yards",
        "Coleman Yards",
        "Santa Clara",
        "1190 Coleman Ave, Santa Clara, CA 95050",
        37.3436,
        -121.9311,
        "Yardstone PM",
        "new_management_spike",
    ),
    DemoBuilding(
        "el-camino-lofts",
        "El Camino Lofts",
        "Santa Clara",
        "3155 El Camino Real, Santa Clara, CA 95051",
        37.3524,
        -121.9843,
        "Lofts SC LLC",
        "parking",
    ),
    DemoBuilding(
        "castro-house",
        "Castro House",
        "Mountain View",
        "801 Castro St, Mountain View, CA 94041",
        37.3894,
        -122.0819,
        "Prometheus",
        "clean",
    ),
    DemoBuilding(
        "whisman-park",
        "Whisman Park Residences",
        "Mountain View",
        "255 N Whisman Rd, Mountain View, CA 94043",
        37.3990,
        -122.0577,
        "Avalon Communities",
        "package_theft",
    ),
    DemoBuilding(
        "stevens-creek-ten",
        "Ten Stevens Creek",
        "Cupertino",
        "19900 Stevens Creek Blvd, Cupertino, CA 95014",
        37.3229,
        -122.0117,
        "Hamilton Properties",
        "water_heat",
    ),
    DemoBuilding(
        "de-anza-court",
        "De Anza Court",
        "Cupertino",
        "10745 N De Anza Blvd, Cupertino, CA 95014",
        37.3355,
        -122.0329,
        "Court Residential",
        "clean",
    ),
    DemoBuilding(
        "japantown-walk",
        "Japantown Walk",
        "San Jose",
        "680 N 6th St, San Jose, CA 95112",
        37.3487,
        -121.8945,
        "Walk Urban Living",
        "management",
    ),
    DemoBuilding(
        "the-alameda-92",
        "92 The Alameda",
        "San Jose",
        "92 The Alameda, San Jose, CA 95126",
        37.3334,
        -121.9142,
        "Alameda Heights PM",
        "safety",
    ),
    DemoBuilding(
        "rosegarden-flats",
        "Rose Garden Flats",
        "San Jose",
        "1300 Naglee Ave, San Jose, CA 95126",
        37.3321,
        -121.9263,
        "Garden City Mgmt",
        "clean",
    ),
]

BUILDINGS_BY_KEY = {b.key: b for b in BUILDINGS}
