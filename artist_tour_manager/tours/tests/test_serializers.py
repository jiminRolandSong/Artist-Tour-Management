"""
Serializer Tests
Tests for serializer validation logic.
"""
from django.test import TestCase
from django.contrib.auth.models import User
from decimal import Decimal
from datetime import date, timedelta

from ..models import Artist, Venue, TourDate, Tour
from ..serializers import TourDateSerializer, RegisterSerializer


class TourDateSerializerValidationTests(TestCase):
    """Tests for TourDateSerializer validation logic."""

    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@test.com',
            password='testpass123'
        )
        self.artist = Artist.objects.create(name='Serializer Artist 1', genre='Rock')
        self.artist2 = Artist.objects.create(name='Serializer Artist 2', genre='Rock')
        self.venue = Venue.objects.create(name='Serializer Venue 1', city='NYC', capacity=20000)
        self.venue2 = Venue.objects.create(name='Serializer Venue 2', city='LA', capacity=18000)
        self.tour = Tour.objects.create(artist=self.artist, name='Serializer Tour')
        self.tour2 = Tour.objects.create(artist=self.artist2, name='Serializer Tour 2')

        self.tour_date = date.today() + timedelta(days=30)

        # Create an existing tour
        self.existing_tour = TourDate.objects.create(
            artist=self.artist,
            tour=self.tour,
            venue=self.venue,
            date=self.tour_date,
            ticket_price=Decimal('100.00'),
            created_by=self.user
        )

    def test_same_artist_same_date_rejected(self):
        """Creating a tour with same artist on same date should fail."""
        data = {
            'tour_id': self.tour.id,
            'artist_id': self.artist.id,
            'venue_id': self.venue2.id,  # Different venue
            'date': self.tour_date,  # Same date
            'ticket_price': '75.00'
        }

        serializer = TourDateSerializer(data=data)

        self.assertFalse(serializer.is_valid())
        self.assertIn('non_field_errors', serializer.errors)

    def test_past_date_rejected(self):
        """Creating a tour in the past should fail."""
        past_date = date.today() - timedelta(days=1)

        data = {
            'tour_id': self.tour.id,
            'artist_id': self.artist.id,
            'venue_id': self.venue.id,
            'date': past_date,
            'ticket_price': '75.00'
        }

        serializer = TourDateSerializer(data=data)

        self.assertFalse(serializer.is_valid())
        self.assertIn('Tour date must be in the future', str(serializer.errors))

    def test_same_artist_different_date_allowed(self):
        """Creating a tour with same artist on different date should succeed."""
        different_date = self.tour_date + timedelta(days=1)

        data = {
            'tour_id': self.tour.id,
            'artist_id': self.artist.id,
            'venue_id': self.venue2.id,
            'date': different_date,
            'ticket_price': '75.00'
        }

        serializer = TourDateSerializer(data=data)

        self.assertTrue(serializer.is_valid(), serializer.errors)

    def test_different_artist_same_date_allowed(self):
        """Creating a tour with different artist on same date should succeed."""
        data = {
            'tour_id': self.tour2.id,
            'artist_id': self.artist2.id,  # Different artist
            'venue_id': self.venue.id,
            'date': self.tour_date,  # Same date
            'ticket_price': '75.00'
        }

        serializer = TourDateSerializer(data=data)

        self.assertTrue(serializer.is_valid(), serializer.errors)

    def test_update_same_tour_same_date_allowed(self):
        """Updating a tour without changing date should not trigger validation error."""
        data = {
            'tour_id': self.tour.id,
            'artist_id': self.artist.id,
            'venue_id': self.venue.id,
            'date': self.tour_date,
            'ticket_price': '150.00'  # Only changing price
        }

        serializer = TourDateSerializer(instance=self.existing_tour, data=data)

        self.assertTrue(serializer.is_valid(), serializer.errors)

    def test_update_to_conflicting_date_rejected(self):
        """Updating a tour to a date that conflicts with another tour should fail."""
        # Create another tour for the same artist
        another_date = self.tour_date + timedelta(days=5)
        another_tour = TourDate.objects.create(
            artist=self.artist,
            tour=self.tour,
            venue=self.venue2,
            date=another_date,
            ticket_price=Decimal('80.00'),
            created_by=self.user
        )

        # Try to update this tour to the same date as existing_tour
        data = {
            'tour_id': self.tour.id,
            'artist_id': self.artist.id,
            'venue_id': self.venue2.id,
            'date': self.tour_date,  # Conflicting date
            'ticket_price': '80.00'
        }

        serializer = TourDateSerializer(instance=another_tour, data=data)

        self.assertFalse(serializer.is_valid())
        self.assertIn('non_field_errors', serializer.errors)


class RegisterSerializerTests(TestCase):
    """Tests for RegisterSerializer."""

    def test_valid_registration(self):
        """Valid registration data should create a user."""
        data = {
            'username': 'newuser',
            'email': 'newuser@test.com',
            'password': 'securepass123'
        }

        serializer = RegisterSerializer(data=data)

        self.assertTrue(serializer.is_valid(), serializer.errors)
        user = serializer.save()

        self.assertEqual(user.username, 'newuser')
        self.assertEqual(user.email, 'newuser@test.com')
        self.assertTrue(user.check_password('securepass123'))

    def test_password_is_write_only(self):
        """Password should not be included in serialized output."""
        user = User.objects.create_user(
            username='testuser',
            email='test@test.com',
            password='testpass123'
        )

        serializer = RegisterSerializer(user)

        self.assertNotIn('password', serializer.data)

    def test_duplicate_username_rejected(self):
        """Registration with existing username should fail."""
        User.objects.create_user(
            username='existinguser',
            email='existing@test.com',
            password='testpass123'
        )

        data = {
            'username': 'existinguser',
            'email': 'new@test.com',
            'password': 'newpass123'
        }

        serializer = RegisterSerializer(data=data)

        self.assertFalse(serializer.is_valid())
        self.assertIn('username', serializer.errors)

    def test_password_is_hashed(self):
        """Password should be hashed, not stored in plain text."""
        data = {
            'username': 'hashtest',
            'email': 'hash@test.com',
            'password': 'mypassword123'
        }

        serializer = RegisterSerializer(data=data)
        serializer.is_valid()
        user = serializer.save()

        # Password should not be stored as plain text
        self.assertNotEqual(user.password, 'mypassword123')
        # But should validate correctly
        self.assertTrue(user.check_password('mypassword123'))
