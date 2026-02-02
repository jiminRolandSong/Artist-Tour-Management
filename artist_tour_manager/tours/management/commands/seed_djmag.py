import random
import re
import urllib.request
from decimal import Decimal

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand

from tours.models import Artist, Venue, FanDemand


DJMAG_TOP100_DJS_URL = "https://djmag.com/top100djs/2024"
DJMAG_TOP100_CLUBS_URL = "https://djmag.com/top100clubs"

CITY_COORDS = [
    ("New York", 40.7128, -74.0060),
    ("Los Angeles", 34.0522, -118.2437),
    ("Chicago", 41.8781, -87.6298),
    ("Houston", 29.7604, -95.3698),
    ("Miami", 25.7617, -80.1918),
    ("Las Vegas", 36.1699, -115.1398),
    ("London", 51.5074, -0.1278),
    ("Paris", 48.8566, 2.3522),
    ("Berlin", 52.5200, 13.4050),
    ("Amsterdam", 52.3676, 4.9041),
    ("Ibiza", 38.9067, 1.4206),
    ("Tokyo", 35.6762, 139.6503),
    ("Seoul", 37.5665, 126.9780),
    ("Sydney", -33.8688, 151.2093),
    ("Toronto", 43.6532, -79.3832),
    ("Mexico City", 19.4326, -99.1332),
]


def _random_city_geo():
    city, lat, lon = random.choice(CITY_COORDS)
    return city, round(lat, 6), round(lon, 6)


def _fetch_html(url):
    with urllib.request.urlopen(url, timeout=20) as resp:
        return resp.read().decode("utf-8", errors="ignore")


def _extract_names(html, pattern):
    raw = re.findall(pattern, html)
    seen = set()
    names = []
    for name in raw:
        cleaned = name.strip()
        if cleaned and cleaned not in seen:
            seen.add(cleaned)
            names.append(cleaned)
        if len(names) >= 100:
            break
    return names


class Command(BaseCommand):
    help = "Seed Artists and Venues from DJ Mag Top 100 lists."

    def add_arguments(self, parser):
        parser.add_argument("--owner", type=str, help="Username to assign as artist owner.")
        parser.add_argument("--with-fandemand", action="store_true", help="Create FanDemand for seeded artists/venues.")
        parser.add_argument("--random-geo", action="store_true", help="Assign random latitude/longitude to venues for testing.")

    def handle(self, *args, **options):
        owner_username = options.get("owner")
        create_fandemand = options.get("with_fandemand")
        random_geo = options.get("random_geo")

        owner = None
        if owner_username:
            owner = User.objects.filter(username=owner_username).first()
            if not owner:
                self.stderr.write(self.style.ERROR(f"Owner user not found: {owner_username}"))
                return

        self.stdout.write("Fetching DJ Mag Top 100 lists...")
        djs_html = _fetch_html(DJMAG_TOP100_DJS_URL)
        clubs_html = _fetch_html(DJMAG_TOP100_CLUBS_URL)

        djs = _extract_names(djs_html, r'/top100djs/2024/\d+/[^"]+">([^<]+)<')
        clubs = _extract_names(clubs_html, r'/top100clubs/2025/\d+/[^"]+">([^<]+)<')

        if len(djs) < 50 or len(clubs) < 50:
            self.stderr.write(self.style.ERROR("Failed to parse enough names from DJ Mag pages."))
            return

        self.stdout.write(f"Seeding {len(djs)} artists and {len(clubs)} venues...")

        for idx, name in enumerate(djs, start=1):
            Artist.objects.get_or_create(
                name=name,
                defaults={
                    "genre": "DJ Mag Top 100",
                    "owner": owner,
                },
            )

        for idx, name in enumerate(clubs, start=1):
            latitude = None
            longitude = None
            city = "Unknown"
            if random_geo:
                city, latitude, longitude = _random_city_geo()

            Venue.objects.get_or_create(
                name=name,
                defaults={
                    "city": city,
                    "capacity": 10000 + (idx * 50),
                    "latitude": latitude,
                    "longitude": longitude,
                    "operating_cost": Decimal("30000.00"),
                },
            )

        if create_fandemand:
            venues = list(Venue.objects.filter(name__in=clubs))
            for artist in Artist.objects.filter(name__in=djs):
                for venue in venues[:10]:
                    FanDemand.objects.get_or_create(
                        artist=artist,
                        venue=venue,
                        defaults={
                            "fan_count": random.randint(50000, 200000),
                            "engagement_score": Decimal("0.10"),
                            "expected_ticket_price": Decimal("120.00"),
                        },
                    )

        self.stdout.write(self.style.SUCCESS("DJ Mag seed complete."))
