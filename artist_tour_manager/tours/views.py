from django.http import HttpResponse
from django.shortcuts import render
import datetime
from decimal import Decimal

# Create your views here.
# queryset = which database records to work with
# serializer_class = how to convert model data <-> JSON
# ViewSet = ALL the CRUD endpoints automatically from q. and s.

from rest_framework import viewsets, generics
from .models import Artist, Venue, TourDate, FanDemand, Tour, TourPlan, OptimizationRun
from django.contrib.auth.models import User
from .serializers import ArtistSerializer, VenueSerializer, TourDateSerializer, RegisterSerializer, OptimizationRequestSerializer, FanDemandSerializer, OptimizationConfirmSerializer, TourSerializer, TourPlanSerializer, OptimizationRunSerializer
from rest_framework.filters import SearchFilter, OrderingFilter
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from .permissions import IsArtistOwner
from rest_framework import status
from rest_framework.exceptions import PermissionDenied
from .optimization import (
    nearest_neighbor_route,
    two_opt,
    score_route,
    estimate_revenue_by_venue,
    ai_adjust_revenue,
    build_schedule,
    filter_venues_by_region,
)

def apply_schedule_to_tour(artist, tour, schedule, conflict_strategy, user):
    conflicts = []
    created = []
    skipped = []
    overwritten = []

    for item in schedule:
        venue_id = item.get('venue_id')
        date_str = item.get('date')
        if not venue_id or not date_str:
            return None, Response({'detail': 'Each schedule item must include venue_id and date.'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            date_value = datetime.date.fromisoformat(date_str)
        except ValueError:
            return None, Response({'detail': f'Invalid date format: {date_str}.'}, status=status.HTTP_400_BAD_REQUEST)
        if date_value <= datetime.date.today():
            return None, Response({'detail': f'Date must be in the future: {date_str}.'}, status=status.HTTP_400_BAD_REQUEST)

        existing = TourDate.objects.filter(artist=artist, date=date_value).first()
        if existing:
            conflicts.append({
                'date': date_str,
                'existing_tour_id': existing.id,
                'existing_venue_id': existing.venue_id,
                'new_venue_id': venue_id,
            })
            if conflict_strategy == 'skip':
                skipped.append(date_str)
                continue
            if conflict_strategy == 'overwrite':
                existing.venue_id = venue_id
                existing.tour = tour
                existing.created_by = user
                demand = FanDemand.objects.filter(artist=artist, venue_id=venue_id).first()
                if demand and demand.expected_ticket_price is not None:
                    existing.ticket_price = demand.expected_ticket_price
                existing.save()
                overwritten.append(existing.id)
                continue

        if existing and not conflict_strategy:
            continue

        demand = FanDemand.objects.filter(artist=artist, venue_id=venue_id).first()
        if demand and demand.expected_ticket_price is not None:
            ticket_price = demand.expected_ticket_price
        else:
            fallback_price = TourDate.objects.filter(artist=artist).order_by('-date').values_list('ticket_price', flat=True).first()
            ticket_price = fallback_price or 0

        created_tour = TourDate.objects.create(
            artist=artist,
            tour=tour,
            venue_id=venue_id,
            date=date_value,
            ticket_price=ticket_price,
            created_by=user,
        )
        created.append(created_tour.id)

    if conflicts and not conflict_strategy:
        return None, Response({
            'detail': 'Conflicts found. Resubmit with conflict_strategy=skip or overwrite.',
            'conflicts': conflicts,
        }, status=status.HTTP_409_CONFLICT)

    return {
        'created_tour_ids': created,
        'overwritten_tour_ids': overwritten,
        'skipped_dates': skipped,
        'conflicts': conflicts,
    }, None

# ViewSets are used to create views for models, allowing for CRUD operations.

class ArtistViewSet(viewsets.ModelViewSet):
    queryset = Artist.objects.all()
    serializer_class = ArtistSerializer
    
    # Check if Authenticated
    permission_classes = [IsAuthenticated]
    
    #Search fields - case-insensitive
    filter_backends = [SearchFilter]
    search_fields = ['name', 'genre']

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)

    def get_queryset(self):
        return Artist.objects.filter(owner=self.request.user)

class VenueViewSet(viewsets.ModelViewSet):
    queryset = Venue.objects.all()
    serializer_class = VenueSerializer
    
    permission_classes = [IsAuthenticated]
    
    filter_backends = [SearchFilter]
    search_fields = ['name', 'city']

class TourViewSet(viewsets.ModelViewSet):
    queryset = Tour.objects.all()
    serializer_class = TourSerializer
    permission_classes = [IsAuthenticated, IsArtistOwner]

    def get_queryset(self):
        return Tour.objects.filter(artist__owner=self.request.user)

    def perform_create(self, serializer):
        artist = serializer.validated_data.get("artist")
        if artist.owner_id != self.request.user.id:
            raise PermissionDenied("Only the artist owner can create tours.")
        tour = serializer.save(created_by=self.request.user)
        venue_ids = serializer.validated_data.get("venue_ids")
        if venue_ids:
            tour.venues.set(Venue.objects.filter(id__in=venue_ids))

    def perform_update(self, serializer):
        tour = serializer.save()
        venue_ids = serializer.validated_data.get("venue_ids")
        if venue_ids is not None:
            tour.venues.set(Venue.objects.filter(id__in=venue_ids))

class TourPlanViewSet(viewsets.ModelViewSet):
    queryset = TourPlan.objects.all()
    serializer_class = TourPlanSerializer
    permission_classes = [IsAuthenticated, IsArtistOwner]

    def get_queryset(self):
        return TourPlan.objects.filter(artist__owner=self.request.user)

    def perform_create(self, serializer):
        artist = serializer.validated_data.get("artist")
        if artist.owner_id != self.request.user.id:
            raise PermissionDenied("Only the artist owner can create plans.")
        serializer.save(created_by=self.request.user)

class FanDemandViewSet(viewsets.ModelViewSet):
    queryset = FanDemand.objects.all()
    serializer_class = FanDemandSerializer
    permission_classes = [IsAuthenticated, IsArtistOwner]

    def get_queryset(self):
        return FanDemand.objects.filter(artist__owner=self.request.user)

    def perform_create(self, serializer):
        artist = serializer.validated_data.get("artist")
        if artist.owner_id != self.request.user.id:
            raise PermissionDenied("Only the artist owner can add fan demand.")
        serializer.save()

from django_filters.rest_framework import DjangoFilterBackend

'''
Filter by:
    artist: /api/tours/?artist=1

    venue: /api/tours/?venue=2

    date: /api/tours/?date=2025-09-01
'''

class TourDateViewSet(viewsets.ModelViewSet):
    queryset = TourDate.objects.all()
    serializer_class = TourDateSerializer
    
    # Check if Authenticated
    permission_classes = [IsAuthenticated, IsArtistOwner]
    
    # Filter, Search, and Ordering
    # DjangoFilterBackend allows filtering by fields defined in filterset_fields
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['artist', 'venue', 'date']
    ordering_fields = ['date', 'ticket_price']
    ordering = ['date']
    search_fields = ['artist__name', 'venue__name']
    
    # Automatically set the user who created the tour date
    def perform_create(self, serializer):
        artist = serializer.validated_data.get("artist")
        if artist.owner_id != self.request.user.id:
            raise PermissionDenied("Only the artist owner can create tours.")
        tour = serializer.validated_data.get("tour")
        if tour.artist_id != artist.id:
            raise PermissionDenied("Tour must belong to the selected artist.")
        serializer.save(created_by=self.request.user)

    def get_queryset(self):
        return TourDate.objects.filter(artist__owner=self.request.user)




# POST-only endpoint / automatically implements .create(), using the serializer
class RegisterView(generics.CreateAPIView):
    queryset = User.objects.all()
    serializer_class = RegisterSerializer
    
    # public endpoint
    permission_classes = []

import csv
from rest_framework.views import APIView
# Export
class TourExportView(APIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        
        print("Query params:", request.query_params)
        print("Format param:", request.query_params.get('format'))
        
        # Get the user and their tours
        # Assuming the user is authenticated and has a TourDate relationship
        user = request.user
        user_tours = TourDate.objects.filter(artist__owner=user)
        
        #csv format
        if request.query_params.get('type', '').lower() == 'csv':
            # Create a CSV response
            response = HttpResponse(content_type='text/csv')
            response['Content-Disposition'] = 'attachment; filename="my_tours.csv"'

            # Write CSV data
            writer = csv.writer(response)
            writer.writerow(['ID', 'Artist', 'Venue', 'Date', 'Ticket Price'])
            for tour in user_tours:
                writer.writerow([tour.id, tour.artist.name, tour.venue.name, tour.date, tour.ticket_price])
            return response

        serializer = TourDateSerializer(user_tours, many=True)
        return Response(serializer.data)


class TourOptimizationView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = OptimizationRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        artist_id = data['artist_id']
        venue_ids = data['venue_ids']
        start_venue_id = data.get('start_venue_id')
        start_city = data.get('start_city')
        cost_per_km = data['cost_per_km']
        distance_weight = data['distance_weight']
        revenue_weight = data['revenue_weight']
        use_ai = data['use_ai']
        start_date = data.get('start_date')
        min_gap_days = data.get('min_gap_days', 0)
        travel_speed_km_per_day = data.get('travel_speed_km_per_day')

        artist = Artist.objects.filter(id=artist_id, owner=request.user).first()
        if not artist:
            return Response({'detail': 'Artist not found or not owned by user.'}, status=status.HTTP_403_FORBIDDEN)

        venues = Venue.objects.filter(id__in=venue_ids)
        if venues.count() != len(venue_ids):
            return Response({'detail': 'One or more venues not found.'}, status=status.HTTP_400_BAD_REQUEST)

        venues_by_id = {v.id: v for v in venues}
        missing_geo = [v.id for v in venues if v.latitude is None or v.longitude is None]
        if missing_geo:
            return Response(
                {'detail': 'All venues must include latitude/longitude.', 'missing_venue_ids': missing_geo},
                status=status.HTTP_400_BAD_REQUEST,
            )

        fan_demands = FanDemand.objects.filter(artist_id=artist_id, venue_id__in=venue_ids)
        fallback_price = TourDate.objects.filter(artist_id=artist_id).order_by('-date').values_list('ticket_price', flat=True).first()
        revenue_by_venue = estimate_revenue_by_venue(fan_demands, fallback_price)
        if not start_venue_id and start_city:
            city_matches = [v for v in venues if v.city and v.city.lower().startswith(start_city.lower())]
            if not city_matches:
                return Response({'detail': 'No venues found for start_city in selected venues.'}, status=status.HTTP_400_BAD_REQUEST)
            start_venue_id = max(
                city_matches,
                key=lambda v: revenue_by_venue.get(v.id, 0),
            ).id
        if use_ai:
            try:
                revenue_by_venue = ai_adjust_revenue(revenue_by_venue, venues_by_id)
            except Exception:
                pass

        baseline_route = venue_ids[:]
        if start_venue_id and start_venue_id in venue_ids:
            baseline_route = [start_venue_id] + [vid for vid in venue_ids if vid != start_venue_id]

        nn_route = nearest_neighbor_route(venue_ids, venues_by_id, start_venue_id)
        optimized_route = two_opt(nn_route, venues_by_id)

        baseline_metrics = score_route(baseline_route, venues_by_id, revenue_by_venue, cost_per_km, distance_weight, revenue_weight)
        optimized_metrics = score_route(optimized_route, venues_by_id, revenue_by_venue, cost_per_km, distance_weight, revenue_weight)

        baseline_distance = baseline_metrics['distance_km']
        optimized_distance = optimized_metrics['distance_km']
        reduction_pct = None
        if baseline_distance > 0:
            reduction_pct = round(((baseline_distance - optimized_distance) / baseline_distance) * 100, 2)

        total_cost = optimized_metrics['total_cost']
        roi = None
        if total_cost > 0:
            roi = round((optimized_metrics['revenue'] - total_cost) / total_cost, 4)

        schedule = build_schedule(
            optimized_route,
            venues_by_id,
            start_date=start_date,
            min_gap_days=min_gap_days,
            travel_speed_km_per_day=travel_speed_km_per_day,
        )

        return Response({
            'artist_id': artist_id,
            'baseline_route': baseline_route,
            'optimized_route': optimized_route,
            'metrics': {
                'baseline_distance_km': baseline_distance,
                'optimized_distance_km': optimized_distance,
                'distance_reduction_pct': reduction_pct,
                'estimated_revenue': optimized_metrics['revenue'],
                'estimated_total_cost': total_cost,
                'estimated_roi': roi,
            },
            'schedule': schedule,
        })


class PlanOptimizationRunView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, plan_id):
        plan = TourPlan.objects.filter(id=plan_id, artist__owner=request.user).first()
        if not plan:
            return Response({'detail': 'Plan not found or not owned by user.'}, status=status.HTTP_404_NOT_FOUND)

        venue_ids = request.data.get('venue_ids') or plan.venue_ids
        if not venue_ids:
            return Response({'detail': 'No venue_ids provided for this plan.'}, status=status.HTTP_400_BAD_REQUEST)

        payload = {
            'artist_id': plan.artist_id,
            'venue_ids': venue_ids,
            'start_city': plan.start_city,
            'start_venue_id': plan.constraints.get('start_venue_id'),
            'use_ai': True,
            'cost_per_km': plan.constraints.get('cost_per_km', '2.00'),
            'distance_weight': plan.constraints.get('distance_weight', '1.0'),
            'revenue_weight': plan.constraints.get('revenue_weight', '1.0'),
            'start_date': plan.start_date,
            'min_gap_days': plan.constraints.get('min_gap_days', 1),
            'travel_speed_km_per_day': plan.constraints.get('travel_speed_km_per_day', '500'),
        }

        serializer = OptimizationRequestSerializer(data=payload)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        artist_id = data['artist_id']
        venues = list(Venue.objects.filter(id__in=venue_ids))
        if len(venues) != len(venue_ids):
            return Response({'detail': 'One or more venues not found.'}, status=status.HTTP_400_BAD_REQUEST)

        filtered_venues, excluded_ids = filter_venues_by_region(venues, plan.region_filters or {})
        if not filtered_venues:
            return Response({'detail': 'No venues match the region filters.'}, status=status.HTTP_400_BAD_REQUEST)
        if excluded_ids:
            venue_ids = [v.id for v in filtered_venues]
            venues = filtered_venues

        venues_by_id = {v.id: v for v in venues}
        missing_geo = [v.id for v in venues if v.latitude is None or v.longitude is None]
        if missing_geo:
            return Response(
                {'detail': 'All venues must include latitude/longitude.', 'missing_venue_ids': missing_geo},
                status=status.HTTP_400_BAD_REQUEST,
            )

        fan_demands = FanDemand.objects.filter(artist_id=artist_id, venue_id__in=venue_ids)
        fallback_price = TourDate.objects.filter(artist_id=artist_id).order_by('-date').values_list('ticket_price', flat=True).first()
        revenue_by_venue = estimate_revenue_by_venue(fan_demands, fallback_price)

        if data.get('use_ai'):
            try:
                revenue_by_venue = ai_adjust_revenue(revenue_by_venue, venues_by_id)
            except Exception:
                pass

        start_venue_id = data.get('start_venue_id')
        if not start_venue_id and data.get('start_city'):
            city_matches = [v for v in venues if v.city and v.city.lower().startswith(data['start_city'].lower())]
            if city_matches:
                start_venue_id = max(city_matches, key=lambda v: revenue_by_venue.get(v.id, 0)).id

        baseline_route = venue_ids[:]
        if start_venue_id and start_venue_id in venue_ids:
            baseline_route = [start_venue_id] + [vid for vid in venue_ids if vid != start_venue_id]

        nn_route = nearest_neighbor_route(venue_ids, venues_by_id, start_venue_id)
        optimized_route = two_opt(nn_route, venues_by_id)

        baseline_metrics = score_route(baseline_route, venues_by_id, revenue_by_venue, data['cost_per_km'], data['distance_weight'], data['revenue_weight'])
        optimized_metrics = score_route(optimized_route, venues_by_id, revenue_by_venue, data['cost_per_km'], data['distance_weight'], data['revenue_weight'])

        baseline_distance = baseline_metrics['distance_km']
        optimized_distance = optimized_metrics['distance_km']
        reduction_pct = None
        if baseline_distance > 0:
            reduction_pct = round(((baseline_distance - optimized_distance) / baseline_distance) * 100, 2)

        total_cost = optimized_metrics['total_cost']
        roi = None
        if total_cost > 0:
            roi = round((optimized_metrics['revenue'] - total_cost) / total_cost, 4)

        schedule = build_schedule(
            optimized_route,
            venues_by_id,
            start_date=data.get('start_date'),
            min_gap_days=data.get('min_gap_days', 0),
            travel_speed_km_per_day=data.get('travel_speed_km_per_day'),
        )

        expected_attendance = 0.0
        for demand in fan_demands:
            expected_attendance += float(Decimal(demand.fan_count) * Decimal(demand.engagement_score))

        warnings = []
        targets = plan.targets or {}
        min_revenue = targets.get('min_revenue')
        min_roi = targets.get('min_roi')
        min_attendance = targets.get('min_attendance')
        if min_revenue and optimized_metrics['revenue'] < float(min_revenue):
            warnings.append('Estimated revenue is below target.')
        if min_roi and roi is not None and roi < float(min_roi):
            warnings.append('Estimated ROI is below target.')
        if min_attendance and expected_attendance < float(min_attendance):
            warnings.append('Estimated attendance is below target.')

        result = {
            'artist_id': artist_id,
            'baseline_route': baseline_route,
            'optimized_route': optimized_route,
            'metrics': {
                'baseline_distance_km': baseline_distance,
                'optimized_distance_km': optimized_distance,
                'distance_reduction_pct': reduction_pct,
                'estimated_revenue': optimized_metrics['revenue'],
                'estimated_total_cost': total_cost,
                'estimated_roi': roi,
                'expected_attendance': round(expected_attendance, 2),
            },
            'schedule': schedule,
            'excluded_venue_ids': excluded_ids,
            'warnings': warnings,
        }

        run = OptimizationRun.objects.create(plan=plan, result=result)
        return Response(OptimizationRunSerializer(run).data)


class OptimizationRunConfirmView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, run_id):
        run = OptimizationRun.objects.filter(id=run_id, plan__artist__owner=request.user).first()
        if not run:
            return Response({'detail': 'Run not found or not owned by user.'}, status=status.HTTP_404_NOT_FOUND)

        tour_id = request.data.get('tour_id')
        conflict_strategy = request.data.get('conflict_strategy')
        if not tour_id:
            return Response({'detail': 'tour_id is required.'}, status=status.HTTP_400_BAD_REQUEST)

        plan = run.plan
        tour = Tour.objects.filter(id=tour_id, artist=plan.artist).first()
        if not tour:
            return Response({'detail': 'Tour not found for this artist.'}, status=status.HTTP_404_NOT_FOUND)

        schedule = request.data.get('schedule') or (run.result or {}).get('schedule') or []
        if not schedule:
            return Response({'detail': 'No schedule available in this run.'}, status=status.HTTP_400_BAD_REQUEST)

        result, error = apply_schedule_to_tour(plan.artist, tour, schedule, conflict_strategy, request.user)
        if error:
            return error
        return Response(result)


class TourOptimizationConfirmView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = OptimizationConfirmSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        artist_id = data['artist_id']
        tour_id = data['tour_id']
        schedule = data['schedule']
        conflict_strategy = data.get('conflict_strategy')

        artist = Artist.objects.filter(id=artist_id, owner=request.user).first()
        if not artist:
            return Response({'detail': 'Artist not found or not owned by user.'}, status=status.HTTP_403_FORBIDDEN)
        tour = Tour.objects.filter(id=tour_id, artist=artist).first()
        if not tour:
            return Response({'detail': 'Tour not found for this artist.'}, status=status.HTTP_404_NOT_FOUND)

        result, error = apply_schedule_to_tour(artist, tour, schedule, conflict_strategy, request.user)
        if error:
            return error
        return Response(result)
