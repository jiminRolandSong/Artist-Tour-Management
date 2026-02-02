"""
Optimization and Fan Demand Tests
Tests for tour optimization endpoints and fan demand functionality.
"""
from django.contrib.auth.models import User
from rest_framework.test import APITestCase, APIClient
from rest_framework import status
from decimal import Decimal
from datetime import date

from ..models import Artist, Venue, TourDate, FanDemand, Tour


class FanDemandAndOptimizationAPITests(APITestCase):
    """Tests for fan demand and optimization endpoints."""

    def setUp(self):
        self.user = User.objects.create_user(
            username='optuser',
            email='opt@test.com',
            password='testpass123'
        )
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

        self.artist = Artist.objects.create(name='Optimizer Artist', genre='Pop', owner=self.user)
        self.tour_group = Tour.objects.create(artist=self.artist, name='Opt Tour', created_by=self.user)

        self.venue1 = Venue.objects.create(
            name='Opt Venue A', city='NYC', capacity=10000,
            latitude=Decimal('40.7505'), longitude=Decimal('-73.9934'),
            operating_cost=Decimal('50000.00')
        )
        self.venue2 = Venue.objects.create(
            name='Opt Venue B', city='Chicago', capacity=12000,
            latitude=Decimal('41.8807'), longitude=Decimal('-87.6742'),
            operating_cost=Decimal('42000.00')
        )
        self.venue3 = Venue.objects.create(
            name='Opt Venue C', city='LA', capacity=15000,
            latitude=Decimal('34.0430'), longitude=Decimal('-118.2673'),
            operating_cost=Decimal('60000.00')
        )

        FanDemand.objects.create(
            artist=self.artist, venue=self.venue1,
            fan_count=100000, engagement_score=Decimal('0.10'),
            expected_ticket_price=Decimal('120.00')
        )
        FanDemand.objects.create(
            artist=self.artist, venue=self.venue2,
            fan_count=80000, engagement_score=Decimal('0.09'),
            expected_ticket_price=Decimal('110.00')
        )
        FanDemand.objects.create(
            artist=self.artist, venue=self.venue3,
            fan_count=90000, engagement_score=Decimal('0.11'),
            expected_ticket_price=Decimal('130.00')
        )

    def test_fan_demand_crud_list(self):
        """Should list all fan demand records for owned artists."""
        response = self.client.get('/api/fan-demand/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 3)

    def test_optimize_returns_metrics(self):
        """Optimization endpoint should return route metrics."""
        payload = {
            'artist_id': self.artist.id,
            'venue_ids': [self.venue1.id, self.venue2.id, self.venue3.id],
            'start_venue_id': self.venue1.id,
            'use_ai': False,
            'cost_per_km': '2.00',
            'distance_weight': '1.0',
            'revenue_weight': '1.0',
            'start_date': '2026-02-15',
            'min_gap_days': 1,
            'travel_speed_km_per_day': '500',
        }
        response = self.client.post('/api/optimize/', payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('metrics', response.data)
        self.assertIn('optimized_route', response.data)
        self.assertIn('distance_reduction_pct', response.data['metrics'])


class OptimizationConfirmAPITests(APITestCase):
    """Tests for optimization schedule confirmation."""

    def setUp(self):
        self.owner = User.objects.create_user(
            username='owner',
            email='owner@test.com',
            password='testpass123'
        )
        self.other = User.objects.create_user(
            username='other',
            email='other@test.com',
            password='testpass123'
        )
        self.artist = Artist.objects.create(name='Confirm Owner Artist', genre='Pop', owner=self.owner)
        self.tour_group = Tour.objects.create(artist=self.artist, name='Confirm Tour', created_by=self.owner)

        self.venue1 = Venue.objects.create(
            name='Confirm Venue A', city='NYC', capacity=10000,
            latitude=Decimal('40.7505'), longitude=Decimal('-73.9934')
        )
        self.venue2 = Venue.objects.create(
            name='Confirm Venue B', city='Chicago', capacity=12000,
            latitude=Decimal('41.8807'), longitude=Decimal('-87.6742')
        )

        FanDemand.objects.create(
            artist=self.artist, venue=self.venue1,
            fan_count=50000, engagement_score=Decimal('0.10'),
            expected_ticket_price=Decimal('100.00')
        )

        self.client = APIClient()

    def test_only_owner_can_confirm(self):
        """Only artist owner should be able to confirm optimization schedule."""
        self.client.force_authenticate(user=self.other)
        payload = {
            'artist_id': self.artist.id,
            'tour_id': self.tour_group.id,
            'schedule': [
                {'venue_id': self.venue1.id, 'date': '2026-02-15'},
            ]
        }
        response = self.client.post('/api/optimize/confirm/', payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_conflict_response_and_overwrite(self):
        """Should detect conflicts and allow overwrite strategy."""
        self.client.force_authenticate(user=self.owner)
        TourDate.objects.create(
            artist=self.artist,
            tour=self.tour_group,
            venue=self.venue1,
            date=date(2026, 2, 15),
            ticket_price=Decimal('90.00'),
            created_by=self.owner
        )

        payload = {
            'artist_id': self.artist.id,
            'tour_id': self.tour_group.id,
            'schedule': [
                {'venue_id': self.venue2.id, 'date': '2026-02-15'},
            ]
        }
        response = self.client.post('/api/optimize/confirm/', payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)
        self.assertIn('conflicts', response.data)

        payload['conflict_strategy'] = 'overwrite'
        response = self.client.post('/api/optimize/confirm/', payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        updated = TourDate.objects.get(artist=self.artist, date=date(2026, 2, 15))
        self.assertEqual(updated.venue_id, self.venue2.id)
