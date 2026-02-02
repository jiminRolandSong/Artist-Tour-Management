"""
Database Constraint Tests
Tests for unique constraints at database and API level.
"""
from django.test import TestCase
from django.contrib.auth.models import User
from django.db import IntegrityError
from rest_framework.test import APITestCase, APIClient
from rest_framework import status
from decimal import Decimal
from datetime import date, timedelta

from ..models import Artist, Venue, TourDate, Tour


class UniqueConstraintTests(TestCase):
    """Tests for database-level unique constraints."""

    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            username='constraintuser',
            email='constraint@test.com',
            password='testpass123'
        )
        self.artist = Artist.objects.create(name='Unique Artist', genre='Rock', owner=self.user)
        self.venue = Venue.objects.create(name='Unique Venue', city='NYC', capacity=10000)
        self.tour_group = Tour.objects.create(artist=self.artist, name='Constraint Tour', created_by=self.user)

    def test_duplicate_artist_name_rejected(self):
        """Database should reject duplicate artist names."""
        with self.assertRaises(IntegrityError):
            Artist.objects.create(name='Unique Artist', genre='Pop')

    def test_duplicate_venue_same_city_rejected(self):
        """Database should reject duplicate venue name in same city."""
        with self.assertRaises(IntegrityError):
            Venue.objects.create(name='Unique Venue', city='NYC', capacity=5000)

    def test_same_venue_name_different_city_allowed(self):
        """Same venue name in different city should be allowed."""
        venue2 = Venue.objects.create(name='Unique Venue', city='LA', capacity=8000)
        self.assertEqual(venue2.name, 'Unique Venue')
        self.assertEqual(venue2.city, 'LA')

    def test_same_artist_same_date_rejected_at_db_level(self):
        """Database should reject same artist booking on same date."""
        tour_date = date.today() + timedelta(days=30)
        TourDate.objects.create(
            artist=self.artist,
            tour=self.tour_group,
            venue=self.venue,
            date=tour_date,
            ticket_price=Decimal('100.00'),
            created_by=self.user
        )
        venue2 = Venue.objects.create(name='Another Venue', city='Chicago', capacity=12000)
        with self.assertRaises(IntegrityError):
            TourDate.objects.create(
                artist=self.artist,
                tour=self.tour_group,
                venue=venue2,
                date=tour_date,  # Same date
                ticket_price=Decimal('80.00'),
                created_by=self.user
            )

    def test_same_date_different_artist_allowed(self):
        """Different artists can book on the same date."""
        tour_date = date.today() + timedelta(days=30)
        TourDate.objects.create(
            artist=self.artist,
            tour=self.tour_group,
            venue=self.venue,
            date=tour_date,
            ticket_price=Decimal('100.00'),
            created_by=self.user
        )
        artist2 = Artist.objects.create(name='Another Artist', genre='Pop', owner=self.user)
        tour_group2 = Tour.objects.create(artist=artist2, name='Constraint Tour 2', created_by=self.user)
        tour2 = TourDate.objects.create(
            artist=artist2,
            tour=tour_group2,
            venue=self.venue,
            date=tour_date,  # Same date, different artist
            ticket_price=Decimal('80.00'),
            created_by=self.user
        )
        self.assertEqual(tour2.date, tour_date)


class UniqueConstraintAPITests(APITestCase):
    """API-level tests for unique constraint error handling."""

    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            username='apiconstraint',
            email='apiconstraint@test.com',
            password='testpass123'
        )
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

        self.artist = Artist.objects.create(name='API Artist', genre='Rock', owner=self.user)
        self.venue = Venue.objects.create(name='API Venue', city='NYC', capacity=10000)

    def test_duplicate_artist_api_returns_400(self):
        """API should return 400 for duplicate artist name."""
        response = self.client.post('/api/artists/', {
            'name': 'API Artist',  # Already exists
            'genre': 'Pop'
        })
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_duplicate_venue_same_city_api_returns_400(self):
        """API should return 400 for duplicate venue in same city."""
        response = self.client.post('/api/venues/', {
            'name': 'API Venue',  # Already exists in NYC
            'city': 'NYC',
            'capacity': 5000
        })
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_same_venue_different_city_api_succeeds(self):
        """API should allow same venue name in different city."""
        response = self.client.post('/api/venues/', {
            'name': 'API Venue',  # Same name but different city
            'city': 'LA',
            'capacity': 8000
        })
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
