"""
API Integration Tests
Tests for REST API endpoints including tours, registration, export, and filtering.
"""
from django.test import TestCase
from django.contrib.auth.models import User
from rest_framework.test import APITestCase, APIClient
from rest_framework import status
from decimal import Decimal
from datetime import date, timedelta

from ..models import Artist, Venue, TourDate, Tour


class TourDateAPITests(APITestCase):
    """Integration tests for TourDate API endpoints."""

    def setUp(self):
        """Set up test data and authentication."""
        self.user1 = User.objects.create_user(
            username='user1',
            email='user1@test.com',
            password='testpass123'
        )
        self.user2 = User.objects.create_user(
            username='user2',
            email='user2@test.com',
            password='testpass123'
        )

        self.artist = Artist.objects.create(name='TourDate API Artist', genre='Alternative', owner=self.user1)
        self.tour_group = Tour.objects.create(artist=self.artist, name='API Tour', created_by=self.user1)
        self.venue = Venue.objects.create(name='TourDate API Venue', city='London', capacity=90000)

        self.tour = TourDate.objects.create(
            artist=self.artist,
            tour=self.tour_group,
            venue=self.venue,
            date=date.today() + timedelta(days=60),
            ticket_price=Decimal('120.00'),
            created_by=self.user1
        )

        self.client = APIClient()

    def test_unauthenticated_access_denied(self):
        """Unauthenticated users should not access tour endpoints."""
        response = self.client.get('/api/tours/')

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_authenticated_user_can_list_tours(self):
        """Authenticated users should be able to list tours."""
        self.client.force_authenticate(user=self.user1)

        response = self.client.get('/api/tours/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_authenticated_user_can_view_tour_detail(self):
        """Authenticated users should be able to view tour details."""
        self.client.force_authenticate(user=self.user1)

        response = self.client.get(f'/api/tours/{self.tour.id}/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['artist']['name'], 'TourDate API Artist')

    def test_owner_can_update_tour(self):
        """Owner should be able to update their tour."""
        self.client.force_authenticate(user=self.user1)

        response = self.client.patch(f'/api/tours/{self.tour.id}/', {
            'ticket_price': '150.00'
        })

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.tour.refresh_from_db()
        self.assertEqual(self.tour.ticket_price, Decimal('150.00'))

    def test_non_owner_cannot_update_tour(self):
        """Non-owner should NOT be able to update others' tours."""
        self.client.force_authenticate(user=self.user2)

        response = self.client.patch(f'/api/tours/{self.tour.id}/', {
            'ticket_price': '200.00'
        })

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_owner_can_delete_tour(self):
        """Owner should be able to delete their tour."""
        self.client.force_authenticate(user=self.user1)

        response = self.client.delete(f'/api/tours/{self.tour.id}/')

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(TourDate.objects.filter(id=self.tour.id).exists())

    def test_non_owner_cannot_delete_tour(self):
        """Non-owner should NOT be able to delete others' tours."""
        self.client.force_authenticate(user=self.user2)

        response = self.client.delete(f'/api/tours/{self.tour.id}/')

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertTrue(TourDate.objects.filter(id=self.tour.id).exists())

    def test_create_tour_sets_created_by(self):
        """Creating a tour should automatically set created_by to current user."""
        # User1 owns the artist, so user1 should be able to create tours
        self.client.force_authenticate(user=self.user1)

        response = self.client.post('/api/tours/', {
            'tour_id': self.tour_group.id,
            'artist_id': self.artist.id,
            'venue_id': self.venue.id,
            'date': (date.today() + timedelta(days=90)).isoformat(),
            'ticket_price': '80.00'
        })

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        new_tour = TourDate.objects.get(id=response.data['id'])
        self.assertEqual(new_tour.created_by, self.user1)

    def test_same_day_booking_rejected_via_api(self):
        """API should reject same-day booking for same artist."""
        self.client.force_authenticate(user=self.user1)

        response = self.client.post('/api/tours/', {
            'tour_id': self.tour_group.id,
            'artist_id': self.artist.id,
            'venue_id': self.venue.id,
            'date': self.tour.date.isoformat(),  # Same date as existing tour
            'ticket_price': '90.00'
        })

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        # Database constraint now enforces this, so error message is different
        self.assertIn('non_field_errors', response.data)

    def test_past_date_rejected_via_api(self):
        """API should reject tours scheduled in the past."""
        self.client.force_authenticate(user=self.user1)

        response = self.client.post('/api/tours/', {
            'tour_id': self.tour_group.id,
            'artist_id': self.artist.id,
            'venue_id': self.venue.id,
            'date': (date.today() - timedelta(days=1)).isoformat(),
            'ticket_price': '90.00'
        })

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('Tour date must be in the future', str(response.data))


class RegistrationAPITests(APITestCase):
    """Integration tests for user registration endpoint."""

    def test_public_registration(self):
        """Registration endpoint should be accessible without authentication."""
        response = self.client.post('/api/register/', {
            'username': 'newuser',
            'email': 'newuser@test.com',
            'password': 'securepass123'
        })

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(User.objects.filter(username='newuser').exists())

    def test_registration_returns_user_data(self):
        """Registration should return user data without password."""
        response = self.client.post('/api/register/', {
            'username': 'datatest',
            'email': 'data@test.com',
            'password': 'securepass123'
        })

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['username'], 'datatest')
        self.assertEqual(response.data['email'], 'data@test.com')
        self.assertNotIn('password', response.data)


class TourExportAPITests(APITestCase):
    """Integration tests for tour export endpoint."""

    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            username='exportuser',
            email='export@test.com',
            password='testpass123'
        )
        self.other_user = User.objects.create_user(
            username='otheruser',
            email='other@test.com',
            password='testpass123'
        )

        self.artist = Artist.objects.create(name='Tour Export Artist', genre='Pop', owner=self.user)
        self.tour_group = Tour.objects.create(artist=self.artist, name='Export Tour', created_by=self.user)
        self.venue = Venue.objects.create(name='Tour Export Venue', city='Chicago', capacity=15000)

        # Create tours for different users, same artist owner
        self.user_tour = TourDate.objects.create(
            artist=self.artist,
            tour=self.tour_group,
            venue=self.venue,
            date=date.today() + timedelta(days=30),
            ticket_price=Decimal('50.00'),
            created_by=self.user
        )
        self.other_tour = TourDate.objects.create(
            artist=self.artist,
            tour=self.tour_group,
            venue=self.venue,
            date=date.today() + timedelta(days=31),
            ticket_price=Decimal('60.00'),
            created_by=self.other_user
        )

        self.client = APIClient()

    def test_export_requires_authentication(self):
        """Export endpoint should require authentication."""
        response = self.client.get('/api/export/tours/')

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_csv_export_returns_csv(self):
        """CSV export should return CSV content type."""
        self.client.force_authenticate(user=self.user)

        response = self.client.get('/api/export/tours/?type=csv')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response['Content-Type'], 'text/csv')
        self.assertIn('attachment', response['Content-Disposition'])

    def test_export_returns_owned_artist_tours(self):
        """Export should include tours for artists owned by the user."""
        self.client.force_authenticate(user=self.user)

        response = self.client.get('/api/export/tours/?type=csv')
        content = response.content.decode('utf-8')

        # Should contain both tours for the owned artist
        self.assertIn('Tour Export Artist', content)
        # Should have 3 lines (header + 2 tours)
        lines = content.strip().split('\n')
        self.assertEqual(len(lines), 3)


class FilterSearchOrderingAPITests(APITestCase):
    """Tests for filtering, searching, and ordering functionality."""

    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            username='filteruser',
            email='filter@test.com',
            password='testpass123'
        )

        self.artist1 = Artist.objects.create(name='Filter Metal Artist', genre='Metal', owner=self.user)
        self.artist2 = Artist.objects.create(name='Filter Pop Artist', genre='Pop', owner=self.user)
        self.tour_group1 = Tour.objects.create(artist=self.artist1, name='Filter Tour 1', created_by=self.user)
        self.tour_group2 = Tour.objects.create(artist=self.artist2, name='Filter Tour 2', created_by=self.user)

        self.venue1 = Venue.objects.create(name='Filter Arena', city='Dallas', capacity=20000)
        self.venue2 = Venue.objects.create(name='Filter Stadium', city='Houston', capacity=50000)

        self.tour1 = TourDate.objects.create(
            artist=self.artist1,
            tour=self.tour_group1,
            venue=self.venue1,
            date=date.today() + timedelta(days=10),
            ticket_price=Decimal('100.00'),
            created_by=self.user
        )
        self.tour2 = TourDate.objects.create(
            artist=self.artist2,
            tour=self.tour_group2,
            venue=self.venue2,
            date=date.today() + timedelta(days=20),
            ticket_price=Decimal('200.00'),
            created_by=self.user
        )

        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

    def test_filter_by_artist(self):
        """Should filter tours by artist."""
        response = self.client.get(f'/api/tours/?artist={self.artist1.id}')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['artist']['name'], 'Filter Metal Artist')

    def test_filter_by_venue(self):
        """Should filter tours by venue."""
        response = self.client.get(f'/api/tours/?venue={self.venue2.id}')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['venue']['name'], 'Filter Stadium')

    def test_search_by_artist_name(self):
        """Should search tours by artist name."""
        response = self.client.get('/api/tours/?search=Pop')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['artist']['name'], 'Filter Pop Artist')

    def test_search_by_venue_name(self):
        """Should search tours by venue name."""
        response = self.client.get('/api/tours/?search=Arena')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['venue']['name'], 'Filter Arena')

    def test_ordering_by_date(self):
        """Should order tours by date."""
        response = self.client.get('/api/tours/?ordering=date')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)
        # First tour should be the earlier date
        self.assertEqual(response.data[0]['artist']['name'], 'Filter Metal Artist')

    def test_ordering_by_ticket_price_descending(self):
        """Should order tours by ticket price descending."""
        response = self.client.get('/api/tours/?ordering=-ticket_price')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)
        # First tour should be the higher price
        self.assertEqual(response.data[0]['artist']['name'], 'Filter Pop Artist')
