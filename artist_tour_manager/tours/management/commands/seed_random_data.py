import random
from datetime import date, timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

from tours.models import Artist, Venue, FanDemand, Tour, TourDate, TourGroupVenue


class Command(BaseCommand):
    help = "Seed random artists, venues, fan demand, tour groups, and tour dates."

    def add_arguments(self, parser):
        parser.add_argument("--owner-username", default="jimin_song", help="Owner username to assign artists.")
        parser.add_argument("--artists", type=int, default=5, help="Number of artists to create.")
        parser.add_argument("--venues", type=int, default=10, help="Number of venues to create.")
        parser.add_argument("--fan-demands", type=int, default=20, help="Number of fan demand rows to create.")
        parser.add_argument("--tour-dates", type=int, default=12, help="Number of tour dates to create.")

    def handle(self, *args, **options):
        User = get_user_model()
        username = options["owner_username"]
        owner, created = User.objects.get_or_create(
            username=username,
            defaults={"email": f"{username}@example.com"},
        )
        if created:
            owner.set_password("demo1234!")
            owner.save()

        artists = []
        for idx in range(options["artists"]):
            name = f"Demo Artist {idx + 1}"
            artist, _ = Artist.objects.get_or_create(
                name=name,
                defaults={"genre": "Electronic", "owner": owner},
            )
            artists.append(artist)

        venues = []
        for idx in range(options["venues"]):
            name = f"Demo Venue {idx + 1}"
            city = random.choice(["New York, USA", "Los Angeles, USA", "Berlin, Germany", "Seoul, Korea", "London, UK"])
            venue, _ = Venue.objects.get_or_create(
                name=name,
                city=city,
                defaults={
                    "capacity": random.randint(2000, 15000),
                    "latitude": Decimal(str(round(random.uniform(-60, 60), 6))),
                    "longitude": Decimal(str(round(random.uniform(-120, 120), 6))),
                    "operating_cost": Decimal(str(random.randint(15000, 60000))),
                    "default_ticket_price": Decimal(str(random.randint(60, 180))),
                },
            )
            venues.append(venue)

        for artist in artists:
            Tour.objects.get_or_create(
                artist=artist,
                name="Default Tour",
                defaults={
                    "start_date": date.today() + timedelta(days=14),
                    "end_date": date.today() + timedelta(days=90),
                    "description": "Auto-generated tour group",
                    "created_by": owner,
                },
            )

        tours = list(Tour.objects.filter(artist__in=artists))
        for tour in tours:
            for venue in random.sample(venues, k=min(5, len(venues))):
                TourGroupVenue.objects.get_or_create(tour=tour, venue=venue)

        for _ in range(options["fan_demands"]):
            artist = random.choice(artists)
            venue = random.choice(venues)
            FanDemand.objects.get_or_create(
                artist=artist,
                venue=venue,
                defaults={
                    "fan_count": random.randint(5000, 60000),
                    "engagement_score": Decimal("0.10"),
                    "expected_ticket_price": Decimal(str(random.randint(70, 160))),
                },
            )

        created_dates = 0
        for _ in range(options["tour_dates"]):
            artist = random.choice(artists)
            tour = Tour.objects.filter(artist=artist).first()
            venue = random.choice(venues)
            date_value = date.today() + timedelta(days=random.randint(7, 120))
            if TourDate.objects.filter(artist=artist, date=date_value).exists():
                continue
            TourDate.objects.create(
                artist=artist,
                tour=tour,
                venue=venue,
                date=date_value,
                ticket_price=venue.default_ticket_price or Decimal("90.00"),
                created_by=owner,
            )
            created_dates += 1

        self.stdout.write(self.style.SUCCESS(
            f"Seeded: artists={len(artists)}, venues={len(venues)}, fan_demands={options['fan_demands']}, tour_dates={created_dates}"
        ))
