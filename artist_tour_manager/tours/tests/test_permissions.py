"""
Permission Tests - IsArtistOwner
Tests for custom permission classes.
"""
from django.test import TestCase
from django.contrib.auth.models import User
from rest_framework.test import APIRequestFactory
from decimal import Decimal
from datetime import date

from ..models import Artist, Venue, TourDate, Tour
from ..permissions import IsArtistOwner


class IsArtistOwnerPermissionTests(TestCase):
    """Tests for the IsArtistOwner custom permission class."""

    def setUp(self):
        """Set up test data."""
        self.factory = APIRequestFactory()
        self.permission = IsArtistOwner()

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
        self.artist = Artist.objects.create(name='Test Artist', genre='Rock', owner=self.user1)
        self.venue = Venue.objects.create(name='Test Venue', city='NYC', capacity=5000)
        self.tour_group = Tour.objects.create(artist=self.artist, name='Perm Tour', created_by=self.user1)
        self.tour = TourDate.objects.create(
            artist=self.artist,
            tour=self.tour_group,
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
