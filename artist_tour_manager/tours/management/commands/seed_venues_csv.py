import csv
from decimal import Decimal

from django.core.management.base import BaseCommand

from tours.models import Venue


class Command(BaseCommand):
    help = "Seed venues from a CSV file with headers: Rank,Name,City,Country,Latitude,Longitude."

    def add_arguments(self, parser):
        parser.add_argument("--file", required=True, help="Path to the CSV file.")
        parser.add_argument("--default-capacity", type=int, default=10000, help="Default venue capacity.")
        parser.add_argument("--operating-cost", type=str, default="30000.00", help="Default operating cost.")

    def handle(self, *args, **options):
        path = options["file"]
        default_capacity = options["default_capacity"]
        operating_cost = Decimal(options["operating_cost"])

        created = 0
        updated = 0
        skipped = 0

        with open(path, newline="", encoding="utf-8") as handle:
            reader = csv.DictReader(handle)
            for row in reader:
                name = (row.get("Name") or "").strip()
                city = (row.get("City") or "").strip()
                country = (row.get("Country") or "").strip()
                lat = row.get("Latitude")
                lon = row.get("Longitude")

                if not name:
                    skipped += 1
                    continue

                city_label = city
                if country:
                    city_label = f"{city}, {country}" if city else country

                venue, created_flag = Venue.objects.get_or_create(
                    name=name,
                    city=city_label or "Unknown",
                    defaults={
                        "capacity": default_capacity,
                        "latitude": Decimal(str(lat)) if lat else None,
                        "longitude": Decimal(str(lon)) if lon else None,
                        "operating_cost": operating_cost,
                    },
                )

                if created_flag:
                    created += 1
                    continue

                changed = False
                if (venue.latitude is None or venue.longitude is None) and lat and lon:
                    venue.latitude = Decimal(str(lat))
                    venue.longitude = Decimal(str(lon))
                    changed = True
                if venue.operating_cost is None:
                    venue.operating_cost = operating_cost
                    changed = True
                if venue.capacity is None:
                    venue.capacity = default_capacity
                    changed = True
                if changed:
                    venue.save()
                    updated += 1
                else:
                    skipped += 1

        self.stdout.write(self.style.SUCCESS(f"Seed complete. created={created}, updated={updated}, skipped={skipped}"))
