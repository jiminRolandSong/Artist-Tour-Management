import datetime
from decimal import Decimal
from django.contrib.auth.models import User
from tours.models import Artist, Venue, FanDemand, Tour, TourPlan
from tours.views import PlanOptimizationRunView, OptimizationRunConfirmView
from rest_framework.test import APIRequestFactory, force_authenticate

user = User.objects.filter(username='jimin_song').first()
if not user:
    raise SystemExit('User jimin_song not found')

stamp = datetime.datetime.now().strftime('%Y%m%d%H%M%S')
artist, _ = Artist.objects.get_or_create(
    name=f'Jimin Song Test Artist {stamp}',
    defaults={'genre': 'Pop', 'owner': user}
)

tour_group, _ = Tour.objects.get_or_create(
    artist=artist,
    name=f'Test Tour {stamp}',
    defaults={'start_date': datetime.date.today() + datetime.timedelta(days=14), 'end_date': datetime.date.today() + datetime.timedelta(days=45), 'created_by': user}
)

venues = []
venue_specs = [
    (f'Test Venue A {stamp}', 'New York, USA', 40.7505, -73.9934),
    (f'Test Venue B {stamp}', 'Chicago, USA', 41.8807, -87.6742),
    (f'Test Venue C {stamp}', 'Los Angeles, USA', 34.0430, -118.2673),
    (f'Test Venue D {stamp}', 'Houston, USA', 29.7508, -95.3621),
]
for name, city, lat, lon in venue_specs:
    v, _ = Venue.objects.get_or_create(
        name=name,
        city=city,
        defaults={'capacity': 15000, 'latitude': Decimal(str(lat)), 'longitude': Decimal(str(lon)), 'operating_cost': Decimal('35000.00')}
    )
    venues.append(v)

for v in venues:
    FanDemand.objects.get_or_create(
        artist=artist,
        venue=v,
        defaults={
            'fan_count': 80000,
            'engagement_score': Decimal('0.10'),
            'expected_ticket_price': Decimal('120.00')
        }
    )

plan, _ = TourPlan.objects.get_or_create(
    artist=artist,
    name=f'Test Plan {stamp}',
    defaults={
        'start_date': datetime.date.today() + datetime.timedelta(days=14),
        'end_date': datetime.date.today() + datetime.timedelta(days=45),
        'start_city': 'New York',
        'venue_ids': [v.id for v in venues],
        'region_filters': {'countries': ['USA']},
        'targets': {'min_revenue': 1000000, 'min_roi': 1.2, 'min_attendance': 20000},
        'constraints': {'min_gap_days': 1, 'travel_speed_km_per_day': 500},
        'created_by': user,
    }
)

factory = APIRequestFactory()
run_view = PlanOptimizationRunView.as_view()
req = factory.post(f'/api/plans/{plan.id}/run/', {}, format='json')
force_authenticate(req, user=user)
run_resp = run_view(req, plan_id=plan.id)

if run_resp.status_code != 200:
    raise SystemExit(f'Run failed: {run_resp.status_code} {run_resp.data}')

run_id = run_resp.data['id']

confirm_view = OptimizationRunConfirmView.as_view()
confirm_req = factory.post(f'/api/runs/{run_id}/confirm/', {
    'tour_id': tour_group.id,
    'conflict_strategy': 'overwrite'
}, format='json')
force_authenticate(confirm_req, user=user)
confirm_resp = confirm_view(confirm_req, run_id=run_id)

print('Created artist_id:', artist.id)
print('Created tour_group_id:', tour_group.id)
print('Created plan_id:', plan.id)
print('Created run_id:', run_id)
print('Confirm response:', confirm_resp.data)
