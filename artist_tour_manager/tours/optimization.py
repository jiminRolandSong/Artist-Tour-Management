import json
import math
import os
from datetime import timedelta
from decimal import Decimal
from urllib import request
from urllib.error import HTTPError, URLError
from decouple import config


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


def estimate_revenue_by_venue(fan_demands, fallback_ticket_price, venues_by_id):
    revenue_by_venue = {}
    for demand in fan_demands:
        venue = venues_by_id.get(demand.venue_id)
        venue_default = venue.default_ticket_price if venue else None
        ticket_price = demand.expected_ticket_price or venue_default or fallback_ticket_price or Decimal('0')
        expected_attendance = Decimal(demand.fan_count) * Decimal(demand.engagement_score)
        if venue and venue.capacity:
            expected_attendance = min(expected_attendance, Decimal(venue.capacity))
        revenue_by_venue[demand.venue_id] = float(expected_attendance * ticket_price)
    return revenue_by_venue


def select_venue_subset(venue_ids, venues_by_id, revenue_by_venue, max_venues, start_venue_id=None, start_city=None):
    if not max_venues or len(venue_ids) <= max_venues:
        return venue_ids

    def add_if_valid(vid, selected, selected_set):
        if vid in selected_set:
            return
        selected.append(vid)
        selected_set.add(vid)

    selected = []
    selected_set = set()

    if start_venue_id and start_venue_id in venue_ids:
        add_if_valid(start_venue_id, selected, selected_set)

    if start_city:
        city_matches = [
            vid for vid in venue_ids
            if venues_by_id.get(vid) and venues_by_id[vid].city and venues_by_id[vid].city.lower().startswith(start_city.lower())
        ]
        if city_matches:
            best_city = max(city_matches, key=lambda vid: revenue_by_venue.get(vid, 0))
            add_if_valid(best_city, selected, selected_set)

    ranked = sorted(
        venue_ids,
        key=lambda vid: revenue_by_venue.get(vid, 0),
        reverse=True,
    )
    for vid in ranked:
        if len(selected) >= max_venues:
            break
        add_if_valid(vid, selected, selected_set)

    # Preserve original order for baseline route
    ordered = [vid for vid in venue_ids if vid in selected_set]
    return ordered


def ai_select_venues(venue_ids, venues_by_id, revenue_by_venue, max_venues, start_city=None, start_venue_id=None):
    if not max_venues or len(venue_ids) <= max_venues:
        return None

    venues_payload = []
    for vid in venue_ids:
        v = venues_by_id.get(vid)
        if not v:
            continue
        venues_payload.append({
            "venue_id": vid,
            "name": v.name,
            "city": v.city,
            "latitude": float(v.latitude) if v.latitude is not None else None,
            "longitude": float(v.longitude) if v.longitude is not None else None,
            "operating_cost": float(v.operating_cost or 0),
            "capacity": int(v.capacity or 0),
            "estimated_revenue": float(revenue_by_venue.get(vid, 0)),
        })

    system_prompt = (
        "You are a tour optimization assistant. "
        "Select a subset of venues that maximizes revenue and minimizes travel cost. "
        "You must return valid JSON with keys: venue_ids (array of ints) and rationale (non-empty string). "
        "Return JSON only."
    )
    user_prompt = (
        "Choose up to max_venues venues. Prefer geographic clustering, include start_venue_id if provided. "
        "Return JSON: {\"venue_ids\": [..], \"rationale\": \"...\"}. Do not omit rationale."
        f"\nmax_venues: {max_venues}"
        f"\nstart_city: {start_city}"
        f"\nstart_venue_id: {start_venue_id}"
        f"\nVenues: {json.dumps(venues_payload)}"
    )

    try:
        result = call_openai_json(system_prompt, user_prompt)
    except HTTPError as exc:
        error_detail = None
        try:
            error_detail = exc.read().decode('utf-8')
        except Exception:
            error_detail = None
        if exc.code == 429:
            rationale = "AI selection rate-limited; used heuristic selection."
        elif exc.code == 401:
            rationale = "AI selection unauthorized; used heuristic selection."
        else:
            rationale = f"AI selection failed (HTTP {exc.code}); used heuristic selection."
        return {
            "venue_ids": None,
            "rationale": rationale,
            "error": f"HTTP {exc.code}",
            "error_detail": error_detail or f"HTTP {exc.code}",
        }
    except URLError as exc:
        return {
            "venue_ids": None,
            "rationale": "AI selection unavailable; used heuristic selection.",
            "error": "unavailable",
            "error_detail": str(exc),
        }
    except Exception as exc:
        return {
            "venue_ids": None,
            "rationale": "AI selection failed; used heuristic selection.",
            "error": "unknown",
            "error_detail": str(exc),
        }

    if not result:
        return {
            "venue_ids": None,
            "rationale": "AI selection unavailable; used heuristic selection.",
            "error": "empty",
            "error_detail": "empty_response",
        }

    ids = result.get("venue_ids") or result.get("selected_venue_ids") or result.get("venues")
    if not isinstance(ids, list):
        return None

    cleaned = []
    seen = set()
    for vid in ids:
        try:
            vid_int = int(vid)
        except (TypeError, ValueError):
            continue
        if vid_int in venue_ids and vid_int not in seen:
            cleaned.append(vid_int)
            seen.add(vid_int)

    if start_venue_id and start_venue_id in venue_ids and start_venue_id not in seen:
        cleaned.insert(0, start_venue_id)

    if max_venues:
        cleaned = cleaned[:max_venues]

    if not cleaned:
        return {
            "venue_ids": None,
            "rationale": "AI selection returned no valid venues; used heuristic selection.",
            "error": "no-valid-venues",
            "error_detail": "no_valid_venue_ids",
        }

    # Preserve original order
    cleaned_set = set(cleaned)
    ordered = [vid for vid in venue_ids if vid in cleaned_set]
    rationale = result.get("rationale")
    if not isinstance(rationale, str) or not rationale.strip():
        rationale = "AI venue selection ran, but no rationale was returned."

    return {
        "venue_ids": ordered,
        "rationale": rationale,
    }


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
    api_key = config('OPENAI_API_KEY', default=os.getenv('OPENAI_API_KEY'))
    if not api_key:
        return None

    payload = {
        'model': config('OPENAI_MODEL', default=os.getenv('OPENAI_MODEL', 'gpt-4o-mini')),
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
