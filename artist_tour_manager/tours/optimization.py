import json
import math
import os
from datetime import timedelta
from decimal import Decimal
from urllib import request


def haversine_km(lat1, lon1, lat2, lon2):
    if None in (lat1, lon1, lat2, lon2):
        return None
    r = 6371.0
    lat1_r = math.radians(float(lat1))
    lon1_r = math.radians(float(lon1))
    lat2_r = math.radians(float(lat2))
    lon2_r = math.radians(float(lon2))
    dlat = lat2_r - lat1_r
    dlon = lon2_r - lon1_r
    a = math.sin(dlat / 2) ** 2 + math.cos(lat1_r) * math.cos(lat2_r) * math.sin(dlon / 2) ** 2
    c = 2 * math.asin(math.sqrt(a))
    return r * c


def total_distance_km(route, venues_by_id):
    total = 0.0
    for i in range(len(route) - 1):
        a = venues_by_id[route[i]]
        b = venues_by_id[route[i + 1]]
        dist = haversine_km(a.latitude, a.longitude, b.latitude, b.longitude)
        if dist is None:
            return None
        total += dist
    return total


def nearest_neighbor_route(venue_ids, venues_by_id, start_id=None):
    if not venue_ids:
        return []
    remaining = set(venue_ids)
    if start_id is None:
        start_id = venue_ids[0]
    if start_id not in remaining:
        start_id = venue_ids[0]
    route = [start_id]
    remaining.remove(start_id)
    while remaining:
        last = venues_by_id[route[-1]]
        next_id = min(
            remaining,
            key=lambda vid: haversine_km(last.latitude, last.longitude, venues_by_id[vid].latitude, venues_by_id[vid].longitude) or float('inf')
        )
        route.append(next_id)
        remaining.remove(next_id)
    return route


def two_opt(route, venues_by_id):
    best = route[:]
    improved = True
    while improved:
        improved = False
        for i in range(1, len(best) - 2):
            for j in range(i + 1, len(best) - 1):
                new_route = best[:]
                new_route[i:j + 1] = reversed(best[i:j + 1])
                if total_distance_km(new_route, venues_by_id) < total_distance_km(best, venues_by_id):
                    best = new_route
                    improved = True
        if not improved:
            break
    return best


def score_route(route, venues_by_id, revenue_by_venue, cost_per_km, distance_weight, revenue_weight):
    distance = total_distance_km(route, venues_by_id) or 0.0
    travel_cost = float(cost_per_km) * distance
    operating_cost = sum(float(venues_by_id[vid].operating_cost or 0) for vid in route)
    revenue = sum(float(revenue_by_venue.get(vid, 0)) for vid in route)
    total_cost = travel_cost + operating_cost
    score = (float(revenue_weight) * revenue) - (float(distance_weight) * distance)
    return {
        'score': score,
        'distance_km': distance,
        'revenue': revenue,
        'total_cost': total_cost,
    }


def estimate_revenue_by_venue(fan_demands, fallback_ticket_price):
    revenue_by_venue = {}
    for demand in fan_demands:
        ticket_price = demand.expected_ticket_price or fallback_ticket_price or Decimal('0')
        expected_attendance = Decimal(demand.fan_count) * Decimal(demand.engagement_score)
        revenue_by_venue[demand.venue_id] = float(expected_attendance * ticket_price)
    return revenue_by_venue


def filter_venues_by_region(venues, region_filters):
    if not region_filters:
        return venues, []

    cities = set((region_filters.get('cities') or []))
    countries = set((region_filters.get('countries') or []))
    continents = set((region_filters.get('continents') or []))
    excluded = []

    def venue_country(v):
        if not v.city:
            return None
        parts = [p.strip() for p in v.city.split(",")]
        if len(parts) >= 2:
            return parts[-1]
        return None

    filtered = []
    for v in venues:
        city_match = True
        country_match = True
        continent_match = True

        if cities:
            city_match = any(v.city and v.city.lower().startswith(c.lower()) for c in cities)
        if countries:
            country = venue_country(v)
            country_match = country and any(country.lower() == c.lower() for c in countries)
        if continents:
            continent_match = False

        if city_match and country_match and continent_match:
            filtered.append(v)
        else:
            excluded.append(v.id)

    return filtered, excluded


def call_openai_json(system_prompt, user_prompt):
    api_key = os.getenv('OPENAI_API_KEY')
    if not api_key:
        return None

    payload = {
        'model': os.getenv('OPENAI_MODEL', 'gpt-4o-mini'),
        'messages': [
            {'role': 'system', 'content': system_prompt},
            {'role': 'user', 'content': user_prompt},
        ],
        'temperature': 0.2,
    }

    req = request.Request(
        'https://api.openai.com/v1/chat/completions',
        data=json.dumps(payload).encode('utf-8'),
        headers={
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {api_key}',
        },
        method='POST',
    )

    with request.urlopen(req, timeout=20) as resp:
        data = json.loads(resp.read().decode('utf-8'))

    # Extract content from Chat Completions API response
    choices = data.get('choices', [])
    if not choices:
        return None
    message = choices[0].get('message', {})
    output_text = message.get('content', '')
    if not output_text:
        return None
    return json.loads(output_text)


def ai_adjust_revenue(revenue_by_venue, venues):
    venues_payload = []
    for vid, revenue in revenue_by_venue.items():
        v = venues[vid]
        venues_payload.append({
            'venue_id': vid,
            'city': v.city,
            'latitude': float(v.latitude) if v.latitude is not None else None,
            'longitude': float(v.longitude) if v.longitude is not None else None,
            'base_revenue': revenue,
        })

    system_prompt = (
        'You are a tour optimization assistant. '
        'Adjust venue revenue estimates based on fan density and geographic clustering. '
        'Return JSON only.'
    )
    user_prompt = (
        'Given the venues list, return a JSON object with a "venue_adjustments" array. '
        'Each item should include venue_id and revenue_multiplier (0.5 to 1.5).'
        f'\nVenues: {json.dumps(venues_payload)}'
    )

    result = call_openai_json(system_prompt, user_prompt)
    if not result or 'venue_adjustments' not in result:
        return revenue_by_venue

    multiplier_by_id = {
        item.get('venue_id'): float(item.get('revenue_multiplier', 1.0))
        for item in result['venue_adjustments']
    }
    adjusted = {}
    for vid, revenue in revenue_by_venue.items():
        adjusted[vid] = revenue * multiplier_by_id.get(vid, 1.0)
    return adjusted


def build_schedule(route, venues_by_id, start_date=None, min_gap_days=0, travel_speed_km_per_day=None):
    if not start_date:
        return []
    schedule = []
    current_date = start_date
    for idx, vid in enumerate(route):
        schedule.append({
            'venue_id': vid,
            'date': current_date.isoformat(),
        })
        if idx < len(route) - 1:
            next_vid = route[idx + 1]
            distance = haversine_km(
                venues_by_id[vid].latitude,
                venues_by_id[vid].longitude,
                venues_by_id[next_vid].latitude,
                venues_by_id[next_vid].longitude,
            )
            travel_days = 0
            if distance is not None and travel_speed_km_per_day:
                travel_days = int(math.ceil(distance / float(travel_speed_km_per_day)))
            gap = max(min_gap_days, travel_days)
            current_date = current_date + timedelta(days=gap)
    return schedule
