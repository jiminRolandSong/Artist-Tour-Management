import random
from decimal import Decimal

from django.core.management.base import BaseCommand

from tours.models import Venue

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


class Command(BaseCommand):
    help = "Randomly fill missing city/latitude/longitude for venues."

    def add_arguments(self, parser):
        parser.add_argument("--all", action="store_true", help="Update all venues, not just missing fields.")
        parser.add_argument("--seed", type=int, help="Random seed for reproducibility.")

    def handle(self, *args, **options):
        if options.get("seed") is not None:
            random.seed(options["seed"])

        if options.get("all"):
            venues = Venue.objects.all()
        else:
            venues = Venue.objects.filter(latitude__isnull=True) | Venue.objects.filter(longitude__isnull=True) | Venue.objects.filter(city="Unknown")

        updated = 0
        for venue in venues:
            city, lat, lon = random.choice(CITY_COORDS)
            if options.get("all") or venue.city in (None, "", "Unknown"):
                venue.city = city
            if options.get("all") or venue.latitude is None:
                venue.latitude = round(lat, 6)
            if options.get("all") or venue.longitude is None:
                venue.longitude = round(lon, 6)
            if venue.operating_cost is None:
                venue.operating_cost = Decimal("30000.00")
            venue.save()
            updated += 1

        self.stdout.write(self.style.SUCCESS(f"Updated {updated} venues."))
