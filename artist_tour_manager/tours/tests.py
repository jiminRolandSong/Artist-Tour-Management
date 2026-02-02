from django.test import TestCase
from django.contrib.auth.models import User
from rest_framework.test import APITestCase, APIClient
from rest_framework import status
from rest_framework.request import Request
from rest_framework.test import APIRequestFactory
from decimal import Decimal
from datetime import date, timedelta

from .models import Artist, Venue, TourDate
from .serializers import TourDateSerializer, RegisterSerializer, ArtistSerializer, VenueSerializer
from .permissions import IsAdminOrReadOnly


# =============================================================================
# PERMISSION TESTS - IsAdminOrReadOnly
# =============================================================================

class IsAdminOrReadOnlyPermissionTests(TestCase):
    """Tests for the IsAdminOrReadOnly custom permission class."""

    def setUp(self):
        """Set up test data."""
        self.factory = APIRequestFactory()
        self.permission = IsAdminOrReadOnly()

        # Create users
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

        # Create test data
        self.artist = Artist.objects.create(name='Test Artist', genre='Rock')
        self.venue = Venue.objects.create(name='Test Venue', city='NYC', capacity=5000)
        self.tour = TourDate.objects.create(
            artist=self.artist,
            venue=self.venue,
            date=date.today(),
            ticket_price=Decimal('50.00'),
            created_by=self.user1
        )

    def test_unauthenticated_user_denied(self):
        """Unauthenticated users should be denied access."""
        request = self.factory.get('/api/tours/')
        request.user = None

        self.assertFalse(self.permission.has_permission(request, None))

    def test_authenticated_user_has_permission(self):
        """Authenticated users should have global permission."""
        request = self.factory.get('/api/tours/')
        request.user = self.user1

        self.assertTrue(self.permission.has_permission(request, None))

    def test_safe_methods_allowed_for_any_authenticated_user(self):
        """GET, HEAD, OPTIONS should be allowed for any authenticated user."""
        safe_methods = ['get', 'head', 'options']

        for method in safe_methods:
            request_func = getattr(self.factory, method)
            request = request_func('/api/tours/1/')
            request.user = self.user2  # Not the owner

            result = self.permission.has_object_permission(request, None, self.tour)
            self.assertTrue(result, f"{method.upper()} should be allowed")

    def test_owner_can_modify_object(self):
        """Owner should be able to PUT, PATCH, DELETE their own objects."""
        unsafe_methods = ['put', 'patch', 'delete']

        for method in unsafe_methods:
            request_func = getattr(self.factory, method)
            request = request_func('/api/tours/1/')
            request.user = self.user1  # The owner

            result = self.permission.has_object_permission(request, None, self.tour)
            self.assertTrue(result, f"Owner should be able to {method.upper()}")

    def test_non_owner_cannot_modify_object(self):
        """Non-owner should NOT be able to PUT, PATCH, DELETE others' objects."""
        unsafe_methods = ['put', 'patch', 'delete']

        for method in unsafe_methods:
            request_func = getattr(self.factory, method)
            request = request_func('/api/tours/1/')
            request.user = self.user2  # Not the owner

            result = self.permission.has_object_permission(request, None, self.tour)
            self.assertFalse(result, f"Non-owner should NOT be able to {method.upper()}")

    def test_post_request_requires_authentication(self):
        """POST requests should require authentication."""
        request = self.factory.post('/api/tours/')
        request.user = self.user1

        self.assertTrue(self.permission.has_permission(request, None))


# =============================================================================
# SERIALIZER VALIDATION TESTS - Same-Day Booking Prevention
# =============================================================================

class TourDateSerializerValidationTests(TestCase):
    """Tests for TourDateSerializer validation logic."""

    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@test.com',
            password='testpass123'
        )
        self.artist = Artist.objects.create(name='Queen', genre='Rock')
        self.artist2 = Artist.objects.create(name='Beatles', genre='Rock')
        self.venue = Venue.objects.create(name='Madison Square Garden', city='NYC', capacity=20000)
        self.venue2 = Venue.objects.create(name='Staples Center', city='LA', capacity=18000)

        self.tour_date = date.today() + timedelta(days=30)

        # Create an existing tour
        self.existing_tour = TourDate.objects.create(
            artist=self.artist,
            venue=self.venue,
            date=self.tour_date,
            ticket_price=Decimal('100.00'),
            created_by=self.user
        )

    def test_same_artist_same_date_rejected(self):
        """Creating a tour with same artist on same date should fail."""
        data = {
            'artist_id': self.artist.id,
            'venue_id': self.venue2.id,  # Different venue
            'date': self.tour_date,  # Same date
            'ticket_price': '75.00'
        }

        serializer = TourDateSerializer(data=data)

        self.assertFalse(serializer.is_valid())
        self.assertIn('non_field_errors', serializer.errors)
        self.assertIn('already has a show on this date', str(serializer.errors))

    def test_same_artist_different_date_allowed(self):
        """Creating a tour with same artist on different date should succeed."""
        different_date = self.tour_date + timedelta(days=1)

        data = {
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
            venue=self.venue2,
            date=another_date,
            ticket_price=Decimal('80.00'),
            created_by=self.user
        )

        # Try to update this tour to the same date as existing_tour
        data = {
            'artist_id': self.artist.id,
            'venue_id': self.venue2.id,
            'date': self.tour_date,  # Conflicting date
            'ticket_price': '80.00'
        }

        serializer = TourDateSerializer(instance=another_tour, data=data)

        self.assertFalse(serializer.is_valid())
        self.assertIn('already has a show on this date', str(serializer.errors))


# =============================================================================
# REGISTRATION SERIALIZER TESTS
# =============================================================================

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


# =============================================================================
# API INTEGRATION TESTS
# =============================================================================

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

        self.artist = Artist.objects.create(name='Coldplay', genre='Alternative')
        self.venue = Venue.objects.create(name='Wembley Stadium', city='London', capacity=90000)

        self.tour = TourDate.objects.create(
            artist=self.artist,
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
        self.client.force_authenticate(user=self.user2)

        response = self.client.get(f'/api/tours/{self.tour.id}/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['artist']['name'], 'Coldplay')

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

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

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

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertTrue(TourDate.objects.filter(id=self.tour.id).exists())

    def test_create_tour_sets_created_by(self):
        """Creating a tour should automatically set created_by to current user."""
        self.client.force_authenticate(user=self.user2)

        response = self.client.post('/api/tours/', {
            'artist_id': self.artist.id,
            'venue_id': self.venue.id,
            'date': (date.today() + timedelta(days=90)).isoformat(),
            'ticket_price': '80.00'
        })

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        new_tour = TourDate.objects.get(id=response.data['id'])
        self.assertEqual(new_tour.created_by, self.user2)

    def test_same_day_booking_rejected_via_api(self):
        """API should reject same-day booking for same artist."""
        self.client.force_authenticate(user=self.user1)

        response = self.client.post('/api/tours/', {
            'artist_id': self.artist.id,
            'venue_id': self.venue.id,
            'date': self.tour.date.isoformat(),  # Same date as existing tour
            'ticket_price': '90.00'
        })

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('already has a show on this date', str(response.data))


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

        self.artist = Artist.objects.create(name='Export Artist', genre='Pop')
        self.venue = Venue.objects.create(name='Export Venue', city='Chicago', capacity=15000)

        # Create tours for different users
        self.user_tour = TourDate.objects.create(
            artist=self.artist,
            venue=self.venue,
            date=date.today() + timedelta(days=30),
            ticket_price=Decimal('50.00'),
            created_by=self.user
        )
        self.other_tour = TourDate.objects.create(
            artist=self.artist,
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

    def test_export_only_returns_users_own_tours(self):
        """Export should only include the authenticated user's tours."""
        self.client.force_authenticate(user=self.user)

        response = self.client.get('/api/export/tours/?type=csv')
        content = response.content.decode('utf-8')

        # Should contain user's tour
        self.assertIn('Export Artist', content)
        # Should only have 2 lines (header + 1 tour)
        lines = content.strip().split('\n')
        self.assertEqual(len(lines), 2)  # Header + 1 tour (not the other user's tour)


class FilterSearchOrderingAPITests(APITestCase):
    """Tests for filtering, searching, and ordering functionality."""

    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            username='filteruser',
            email='filter@test.com',
            password='testpass123'
        )

        self.artist1 = Artist.objects.create(name='Metallica', genre='Metal')
        self.artist2 = Artist.objects.create(name='Taylor Swift', genre='Pop')

        self.venue1 = Venue.objects.create(name='Arena', city='Dallas', capacity=20000)
        self.venue2 = Venue.objects.create(name='Stadium', city='Houston', capacity=50000)

        self.tour1 = TourDate.objects.create(
            artist=self.artist1,
            venue=self.venue1,
            date=date.today() + timedelta(days=10),
            ticket_price=Decimal('100.00'),
            created_by=self.user
        )
        self.tour2 = TourDate.objects.create(
            artist=self.artist2,
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
        self.assertEqual(response.data[0]['artist']['name'], 'Metallica')

    def test_filter_by_venue(self):
        """Should filter tours by venue."""
        response = self.client.get(f'/api/tours/?venue={self.venue2.id}')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['venue']['name'], 'Stadium')

    def test_search_by_artist_name(self):
        """Should search tours by artist name."""
        response = self.client.get('/api/tours/?search=Taylor')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['artist']['name'], 'Taylor Swift')

    def test_search_by_venue_name(self):
        """Should search tours by venue name."""
        response = self.client.get('/api/tours/?search=Arena')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['venue']['name'], 'Arena')

    def test_ordering_by_date(self):
        """Should order tours by date."""
        response = self.client.get('/api/tours/?ordering=date')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)
        # First tour should be the earlier date
        self.assertEqual(response.data[0]['artist']['name'], 'Metallica')

    def test_ordering_by_ticket_price_descending(self):
        """Should order tours by ticket price descending."""
        response = self.client.get('/api/tours/?ordering=-ticket_price')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)
        # First tour should be the higher price
        self.assertEqual(response.data[0]['artist']['name'], 'Taylor Swift')
