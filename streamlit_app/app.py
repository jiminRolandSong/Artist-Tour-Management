import math
import os
from datetime import date, timedelta

import pydeck as pdk
import requests
import streamlit as st

from api_client import (
    confirm_optimization,
    create_artist,
    create_tour_group,
    get_artists,
    get_tour_dates,
    get_tour_groups,
    get_venues,
    login,
    register,
    run_optimization,
)


st.set_page_config(page_title="Artist Tour Optimizer", layout="wide")


def init_state():
    defaults = {
        "api_base_url": os.environ.get("API_BASE_URL", "http://localhost:8000"),
        "access_token": None,
        "artists": [],
        "venues": [],
        "tour_groups": [],
        "tour_dates": [],
        "optimization_result": None,
        "selected_artist_id": None,
        "selected_venue_ids": [],
    }
    for key, value in defaults.items():
        st.session_state.setdefault(key, value)


def get_access_token():
    return st.session_state.get("access_token")


def require_login():
    if get_access_token():
        return True
    st.info("Log in from the Account tab to use this workflow.")
    return False


def list_response_items(data):
    if isinstance(data, dict) and "results" in data:
        return data["results"]
    return data if isinstance(data, list) else []


def display_error(error):
    response = getattr(error, "response", None)
    if response is not None:
        try:
            data = response.json()
            if isinstance(data, dict) and data.get("detail"):
                st.error(data["detail"])
            else:
                st.error(data)
            return
        except ValueError:
            pass
    st.error(str(error))


def refresh_account_data():
    token = get_access_token()
    if not token:
        return
    api_base_url = st.session_state["api_base_url"]
    st.session_state["artists"] = list_response_items(get_artists(api_base_url, token))
    st.session_state["venues"] = list_response_items(get_venues(api_base_url, token))
    st.session_state["tour_groups"] = list_response_items(get_tour_groups(api_base_url, token))
    st.session_state["tour_dates"] = list_response_items(get_tour_dates(api_base_url, token))


def venue_country(venue):
    city = venue.get("city")
    if not city:
        return None
    parts = [part.strip() for part in city.split(",")]
    return parts[-1] if len(parts) >= 2 else None


def venue_city_name(venue):
    city = venue.get("city")
    if not city:
        return None
    return city.split(",")[0].strip()


def venue_display_name(venue):
    return f"{venue.get('name', 'Venue')} - {venue.get('city', 'Unknown city')} (ID {venue['id']})"


def parse_float(value):
    if value in (None, ""):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def haversine_km(lat1, lon1, lat2, lon2):
    if None in (lat1, lon1, lat2, lon2):
        return None
    radius_km = 6371.0
    lat1_r = math.radians(lat1)
    lon1_r = math.radians(lon1)
    lat2_r = math.radians(lat2)
    lon2_r = math.radians(lon2)
    dlat = lat2_r - lat1_r
    dlon = lon2_r - lon1_r
    a = math.sin(dlat / 2) ** 2 + math.cos(lat1_r) * math.cos(lat2_r) * math.sin(dlon / 2) ** 2
    return radius_km * 2 * math.asin(math.sqrt(a))


def leg_distance_km(from_venue, to_venue):
    return haversine_km(
        parse_float(from_venue.get("latitude")),
        parse_float(from_venue.get("longitude")),
        parse_float(to_venue.get("latitude")),
        parse_float(to_venue.get("longitude")),
    )


def artist_options(artists):
    return {f"{artist.get('name', 'Artist')} (ID {artist['id']})": artist["id"] for artist in artists}


def artist_rows(artists):
    return [
        {
            "artist": artist.get("name", ""),
            "genre": artist.get("genre", ""),
            "artist_id": artist.get("id"),
        }
        for artist in artists
    ]


def filter_venues_by_region(venues, selected_cities=None, selected_countries=None):
    selected_cities = set(selected_cities or [])
    selected_countries = set(selected_countries or [])
    filtered = []
    excluded = []

    for venue in venues:
        city = venue_city_name(venue)
        country = venue_country(venue)
        city_match = not selected_cities or city in selected_cities
        country_match = not selected_countries or country in selected_countries
        if city_match and country_match:
            filtered.append(venue)
        else:
            excluded.append(venue["id"])

    return filtered, excluded


def route_rows(route, venue_by_id, revenue_by_venue=None):
    revenue_by_venue = revenue_by_venue or {}
    rows = []
    for index, venue_id in enumerate(route, start=1):
        venue = venue_by_id.get(venue_id, {})
        revenue = revenue_by_venue.get(str(venue_id), revenue_by_venue.get(venue_id))
        revenue_display = f"${float(revenue):,.0f}" if revenue not in (None, "") else ""
        rows.append({
            "stop": index,
            "venue": venue.get("name", "Unknown venue"),
            "city": venue_city_name(venue) or venue.get("city", ""),
            "country": venue_country(venue) or "",
            "estimated_revenue": revenue_display,
            "venue_id": venue_id,
        })
    return rows


def route_leg_rows(route, venue_by_id):
    rows = []
    for index, (from_id, to_id) in enumerate(zip(route, route[1:]), start=1):
        from_venue = venue_by_id.get(from_id, {})
        to_venue = venue_by_id.get(to_id, {})
        distance = leg_distance_km(from_venue, to_venue)
        rows.append({
            "leg": index,
            "from": from_venue.get("name", "Unknown venue"),
            "to": to_venue.get("name", "Unknown venue"),
            "from_city": venue_city_name(from_venue) or from_venue.get("city", ""),
            "to_city": venue_city_name(to_venue) or to_venue.get("city", ""),
            "distance_km": round(distance, 1) if distance is not None else "",
        })
    return rows


def selected_venue_rows(venue_ids, venue_by_id):
    rows = []
    for index, venue_id in enumerate(venue_ids, start=1):
        venue = venue_by_id.get(venue_id, {})
        rows.append({
            "selection": index,
            "venue": venue.get("name", "Unknown venue"),
            "city": venue_city_name(venue) or venue.get("city", ""),
            "country": venue_country(venue) or "",
            "capacity": venue.get("capacity", ""),
            "venue_id": venue_id,
        })
    return rows


def revenue_lookup(result):
    revenue_by_venue = result.get("revenue_by_venue") or result.get("estimated_revenue_by_venue") or {}
    if revenue_by_venue:
        return revenue_by_venue

    lookup = {}
    for item in result.get("venue_revenues") or []:
        venue_id = item.get("venue_id")
        if venue_id is not None:
            lookup[venue_id] = item.get("estimated_revenue")
    return lookup


def result_insight_rows(result, metrics, cost_per_km):
    baseline_distance = float(metrics.get("baseline_distance_km") or 0)
    optimized_distance = float(metrics.get("optimized_distance_km") or 0)
    distance_saved = baseline_distance - optimized_distance
    distance_pct = metrics.get("distance_reduction_pct")
    revenue = float(metrics.get("estimated_revenue") or 0)
    total_cost = float(metrics.get("estimated_total_cost") or 0)
    profit = revenue - total_cost
    selected_count = len(result.get("selected_venue_ids") or [])
    travel_cost = optimized_distance * float(cost_per_km or 0)
    operating_cost = max(total_cost - travel_cost, 0)

    return [
        {"metric": "Selected venues", "value": f"{selected_count:,}"},
        {"metric": "Route distance removed", "value": f"{distance_saved:,.1f} km"},
        {"metric": "Distance reduction", "value": f"{distance_pct if distance_pct is not None else 0}%"},
        {"metric": "Estimated revenue", "value": f"${revenue:,.0f}"},
        {"metric": "Estimated total cost", "value": f"${total_cost:,.0f}"},
        {"metric": "Estimated profit", "value": f"${profit:,.0f}"},
        {"metric": "Estimated travel cost", "value": f"${travel_cost:,.0f}"},
        {"metric": "Estimated operating cost", "value": f"${operating_cost:,.0f}"},
        {"metric": "Selection strategy", "value": result.get("selection_strategy") or "direct"},
    ]


def route_change_summary(result, metrics):
    baseline = result.get("baseline_route") or []
    optimized = result.get("optimized_route") or []
    if not baseline or not optimized:
        return "No route comparison is available."

    moved_stops = sum(1 for index, venue_id in enumerate(optimized) if index >= len(baseline) or baseline[index] != venue_id)
    reduction_pct = float(metrics.get("distance_reduction_pct") or 0)
    if reduction_pct < 1:
        return (
            f"The optimizer changed {moved_stops} stop positions, but the selected order was already close to the optimized route. "
            "That is why distance savings are small while revenue and ROI still remain the main decision metrics."
        )
    return f"The optimizer changed {moved_stops} stop positions and reduced travel distance by {reduction_pct}%."


def schedule_rows(schedule, venue_by_id):
    rows = []
    for index, item in enumerate(schedule, start=1):
        venue_id = item.get("venue_id")
        venue = venue_by_id.get(venue_id, {})
        rows.append({
            "stop": index,
            "date": item.get("date"),
            "venue": venue.get("name", "Unknown venue"),
            "city": venue_city_name(venue) or venue.get("city", ""),
            "country": venue_country(venue) or "",
            "venue_id": venue_id,
        })
    return rows


def tour_date_rows(tour_dates):
    rows = []
    for item in tour_dates:
        artist = item.get("artist") or {}
        venue = item.get("venue") or {}
        rows.append({
            "date": item.get("date"),
            "artist": artist.get("name", ""),
            "tour": item.get("tour_name", ""),
            "venue": venue.get("name", ""),
            "city": venue_city_name(venue) or venue.get("city", ""),
            "country": venue_country(venue) or "",
            "ticket_price": item.get("ticket_price"),
        })
    return rows


def tour_group_rows(tour_groups):
    artists_by_id = {artist["id"]: artist.get("name", "") for artist in st.session_state.get("artists", [])}
    rows = []
    for group in tour_groups:
        rows.append({
            "tour": group.get("name", ""),
            "artist": artists_by_id.get(group.get("artist"), group.get("artist_name", "")),
            "start_date": group.get("start_date"),
            "end_date": group.get("end_date"),
            "venues": len(group.get("venues") or []),
            "tour_id": group.get("id"),
        })
    return rows


def render_sidebar():
    with st.sidebar:
        st.subheader("Session")
        st.caption("Connected" if get_access_token() else "Not logged in")
        if get_access_token() and st.button("Quick refresh"):
            try:
                refresh_account_data()
                st.success("Data refreshed")
            except requests.RequestException as error:
                display_error(error)

        if get_access_token() and st.button("Log out"):
            st.session_state["access_token"] = None
            st.session_state["optimization_result"] = None
            st.session_state["artists"] = []
            st.session_state["venues"] = []
            st.session_state["tour_groups"] = []
            st.session_state["tour_dates"] = []
            st.rerun()


def render_account_tab():
    st.subheader("Account")
    st.session_state["api_base_url"] = st.text_input("API base URL", value=st.session_state["api_base_url"])

    col1, col2 = st.columns(2)
    with col1:
        st.write("Log in")
        username = st.text_input("Username", key="login_username")
        password = st.text_input("Password", type="password", key="login_password")
        if st.button("Log in", type="primary"):
            try:
                tokens = login(st.session_state["api_base_url"], username, password)
                st.session_state["access_token"] = tokens["access"]
                refresh_account_data()
                st.rerun()
            except (KeyError, requests.RequestException) as error:
                display_error(error)

    with col2:
        st.write("Create account")
        new_username = st.text_input("New username")
        new_email = st.text_input("Email")
        new_password = st.text_input("New password", type="password")
        if st.button("Create account"):
            try:
                register(st.session_state["api_base_url"], new_username, new_email, new_password)
                st.success("Account created. Log in to continue.")
            except requests.RequestException as error:
                display_error(error)

    if get_access_token():
        st.divider()
        st.write("Loaded data")
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Artists", len(st.session_state["artists"]))
        c2.metric("Venues", len(st.session_state["venues"]))
        c3.metric("Tour groups", len(st.session_state["tour_groups"]))
        c4.metric("Tour dates", len(st.session_state["tour_dates"]))
        if st.button("Refresh account data"):
            try:
                refresh_account_data()
                st.success("Data refreshed")
            except requests.RequestException as error:
                display_error(error)

        st.divider()
        render_artist_manager()


def render_create_artist_form(key_prefix):
    with st.form(f"{key_prefix}_create_artist_form"):
        name = st.text_input("Artist name", key=f"{key_prefix}_artist_name")
        genre = st.text_input("Genre", key=f"{key_prefix}_artist_genre")
        submitted = st.form_submit_button("Create artist")

    if not submitted:
        return

    if not name.strip() or not genre.strip():
        st.warning("Artist name and genre are required.")
        return

    try:
        artist = create_artist(st.session_state["api_base_url"], get_access_token(), name.strip(), genre.strip())
        st.session_state["selected_artist_id"] = artist.get("id")
        refresh_account_data()
        st.success(f"Created artist: {artist.get('name', name.strip())}")
        st.rerun()
    except requests.RequestException as error:
        display_error(error)


def render_artist_manager():
    st.subheader("Artists")
    artists = st.session_state.get("artists", [])
    col1, col2 = st.columns([2, 1])

    with col1:
        if artists:
            st.dataframe(artist_rows(artists), use_container_width=True, hide_index=True)
        else:
            st.info("No artists yet. Create one to start optimizing tours.")

    with col2:
        st.write("Add artist")
        render_create_artist_form("account")


def render_venue_filters(venues, key_prefix):
    available_countries = sorted({venue_country(venue) for venue in venues if venue_country(venue)})
    country_filter = st.multiselect("Countries", options=available_countries, key=f"{key_prefix}_country_filter")

    country_filtered_venues, _ = filter_venues_by_region(venues, selected_countries=country_filter)
    available_cities = sorted({
        venue_city_name(venue)
        for venue in country_filtered_venues
        if venue_city_name(venue)
    })
    city_filter = st.multiselect("Cities", options=available_cities, key=f"{key_prefix}_city_filter")

    filtered_venues, excluded_venue_ids = filter_venues_by_region(
        venues,
        selected_cities=city_filter,
        selected_countries=country_filter,
    )
    st.caption(f"Showing {len(filtered_venues)} of {len(venues)} venues. Excluded {len(excluded_venue_ids)}.")
    return filtered_venues


def render_route_map(baseline_route, optimized_route, venue_by_id):
    def route_to_arcs(route, color):
        arcs = []
        for from_id, to_id in zip(route, route[1:]):
            src = venue_by_id.get(from_id, {})
            tgt = venue_by_id.get(to_id, {})
            src_lat = parse_float(src.get("latitude"))
            src_lon = parse_float(src.get("longitude"))
            tgt_lat = parse_float(tgt.get("latitude"))
            tgt_lon = parse_float(tgt.get("longitude"))
            if None in (src_lat, src_lon, tgt_lat, tgt_lon):
                continue
            arcs.append({
                "src_lat": src_lat, "src_lon": src_lon,
                "tgt_lat": tgt_lat, "tgt_lon": tgt_lon,
                "src_name": src.get("name", ""), "tgt_name": tgt.get("name", ""),
                "color": color,
            })
        return arcs

    def route_to_points(route, color):
        points = []
        for venue_id in route:
            v = venue_by_id.get(venue_id, {})
            lat = parse_float(v.get("latitude"))
            lon = parse_float(v.get("longitude"))
            if None in (lat, lon):
                continue
            points.append({"lat": lat, "lon": lon, "name": v.get("name", ""), "color": color})
        return points

    baseline_arcs = route_to_arcs(baseline_route, [255, 100, 100, 160])
    optimized_arcs = route_to_arcs(optimized_route, [100, 220, 255, 200])
    all_points = route_to_points(list(dict.fromkeys(baseline_route + optimized_route)), [255, 255, 255, 220])

    if not optimized_arcs and not baseline_arcs:
        st.info("No venue coordinates available to render the map.")
        return

    arc_layer = pdk.Layer(
        "ArcLayer",
        data=baseline_arcs + optimized_arcs,
        get_source_position=["src_lon", "src_lat"],
        get_target_position=["tgt_lon", "tgt_lat"],
        get_source_color="color",
        get_target_color="color",
        get_width=2,
        pickable=True,
    )
    scatter_layer = pdk.Layer(
        "ScatterplotLayer",
        data=all_points,
        get_position=["lon", "lat"],
        get_fill_color="color",
        get_radius=60000,
        pickable=True,
    )

    first_id = (optimized_route or baseline_route or [None])[0]
    first_venue = venue_by_id.get(first_id, {}) if first_id else {}
    center_lat = parse_float(first_venue.get("latitude")) or 20
    center_lon = parse_float(first_venue.get("longitude")) or 0

    view = pdk.ViewState(latitude=center_lat, longitude=center_lon, zoom=2, pitch=30)
    st.pydeck_chart(pdk.Deck(
        layers=[arc_layer, scatter_layer],
        initial_view_state=view,
        tooltip={"text": "{src_name} → {tgt_name}\n{name}"},
        map_style="mapbox://styles/mapbox/dark-v10",
    ))
    col1, col2 = st.columns(2)
    col1.markdown("🔴 Baseline route")
    col2.markdown("🔵 Optimized route")


def render_optimize_tab():
    if not require_login():
        return

    artists = st.session_state["artists"]
    venues = st.session_state["venues"]
    if not artists:
        st.warning("No artists returned for this account.")
        st.write("Create an artist to start building routes.")
        render_create_artist_form("opt_empty")
        return
    if not venues:
        st.warning("No venues are available.")
        return

    venue_by_id = {venue["id"]: venue for venue in venues}
    options = artist_options(artists)

    st.subheader("1. Select Artist")
    current_artist_index = 0
    if st.session_state.get("selected_artist_id") in options.values():
        current_artist_index = list(options.values()).index(st.session_state["selected_artist_id"])
    artist_label = st.selectbox("Artist", options=list(options.keys()), index=current_artist_index)
    artist_id = options[artist_label]
    st.session_state["selected_artist_id"] = artist_id
    with st.expander("Add another artist", expanded=False):
        render_create_artist_form("opt")

    st.subheader("2. Filter Venues")
    filtered_venues = render_venue_filters(venues, "opt")
    venue_options = {venue_display_name(venue): venue["id"] for venue in filtered_venues}
    venue_labels = st.multiselect("Venues", options=list(venue_options.keys()), key="opt_venue_labels")
    selected_venue_ids = [venue_options[label] for label in venue_labels]
    selected_venues = [venue_by_id[venue_id] for venue_id in selected_venue_ids]
    st.session_state["selected_venue_ids"] = selected_venue_ids

    c1, c2, c3 = st.columns(3)
    c1.metric("Selected venues", len(selected_venue_ids))
    c2.metric("Countries", len({venue_country(venue) for venue in selected_venues if venue_country(venue)}))
    c3.metric("Cities", len({venue_city_name(venue) for venue in selected_venues if venue_city_name(venue)}))

    if selected_venues:
        st.write("Selected venues")
        st.dataframe(selected_venue_rows(selected_venue_ids, venue_by_id), use_container_width=True, hide_index=True)

    st.subheader("3. Configure Optimization")
    settings_left, settings_right = st.columns(2)
    with settings_left:
        selected_start_cities = sorted({venue.get("city") for venue in selected_venues if venue.get("city")})
        start_city_label = st.selectbox("Start city", options=["No preference", *selected_start_cities])
        start_date = st.date_input("Start date", value=date.today() + timedelta(days=30))
        max_venues = st.number_input("Max venues", min_value=0, value=0, help="Use 0 for no limit.")
        min_gap_days = st.number_input("Minimum gap days", min_value=0, value=1)

    with settings_right:
        cost_per_km = st.number_input("Cost per km", min_value=0.0, value=2.0, step=0.25)
        travel_speed_km_per_day = st.number_input("Travel speed km/day", min_value=1.0, value=500.0, step=25.0)
        use_ai = st.checkbox("Use AI revenue adjustment")
        use_ai_selection = st.checkbox("Use AI venue selection")

    ai_ready = bool(max_venues and len(selected_venue_ids) > max_venues and use_ai_selection)
    if use_ai_selection:
        if ai_ready:
            st.info(f"AI venue selection will choose up to {int(max_venues)} of {len(selected_venue_ids)} venues.")
        else:
            st.warning("AI venue selection only runs when Max venues is greater than 0 and below the selected venue count.")

    if st.button("Run optimization", type="primary", disabled=not selected_venue_ids):
        payload = {
            "artist_id": artist_id,
            "venue_ids": selected_venue_ids,
            "use_ai": use_ai,
            "use_ai_selection": use_ai_selection,
            "cost_per_km": str(cost_per_km),
            "distance_weight": "1.0",
            "revenue_weight": "1.0",
            "start_date": start_date.isoformat(),
            "min_gap_days": int(min_gap_days),
            "travel_speed_km_per_day": str(travel_speed_km_per_day),
        }
        if start_city_label != "No preference":
            payload["start_city"] = start_city_label
        if max_venues:
            payload["max_venues"] = int(max_venues)

        try:
            st.session_state["optimization_result"] = run_optimization(
                st.session_state["api_base_url"],
                get_access_token(),
                payload,
            )
        except requests.RequestException as error:
            display_error(error)

    result = st.session_state.get("optimization_result")
    if not result:
        return

    st.subheader("4. Review Result")
    if result.get("baseline_route") or result.get("optimized_route"):
        st.subheader("Route Map")
        render_route_map(
            result.get("baseline_route", []),
            result.get("optimized_route", []),
            venue_by_id,
        )
    metrics = result.get("metrics") or {}
    if metrics:
        metric_cols = st.columns(5)
        metric_cols[0].metric("Baseline km", f"{metrics.get('baseline_distance_km', 0):,.1f}")
        metric_cols[1].metric("Optimized km", f"{metrics.get('optimized_distance_km', 0):,.1f}")
        metric_cols[2].metric("Distance saved", f"{metrics.get('distance_reduction_pct') or 0}%")
        metric_cols[3].metric("Revenue", f"${metrics.get('estimated_revenue', 0):,.0f}")
        metric_cols[4].metric("ROI", metrics.get("estimated_roi", "n/a"))

    route_tab, legs_tab, schedule_tab, raw_tab = st.tabs(["Summary", "Route Legs", "Schedule", "Raw JSON"])
    revenue_by_venue = revenue_lookup(result)
    if not revenue_by_venue:
        st.warning("This optimization result does not include per-venue revenue. Run optimization again to refresh the result.")

    with route_tab:
        st.info(route_change_summary(result, metrics))
        st.dataframe(
            result_insight_rows(result, metrics, cost_per_km),
            use_container_width=True,
            hide_index=True,
        )

        col1, col2 = st.columns(2)
        col1.write("Baseline route")
        col1.dataframe(
            route_rows(result.get("baseline_route", []), venue_by_id, revenue_by_venue),
            use_container_width=True,
            hide_index=True,
        )
        col2.write("Optimized route")
        col2.dataframe(
            route_rows(result.get("optimized_route", []), venue_by_id, revenue_by_venue),
            use_container_width=True,
            hide_index=True,
        )

    with legs_tab:
        col1, col2 = st.columns(2)
        col1.write("Baseline legs")
        col1.dataframe(
            route_leg_rows(result.get("baseline_route", []), venue_by_id),
            use_container_width=True,
            hide_index=True,
        )
        col2.write("Optimized legs")
        col2.dataframe(
            route_leg_rows(result.get("optimized_route", []), venue_by_id),
            use_container_width=True,
            hide_index=True,
        )

    with schedule_tab:
        schedule = result.get("schedule") or []
        if schedule:
            st.dataframe(schedule_rows(schedule, venue_by_id), use_container_width=True, hide_index=True)
        else:
            st.info("No schedule returned. Choose a start date and run optimization again.")

    with raw_tab:
        st.json(result)

    if result.get("selection_rationale") or result.get("selection_error"):
        with st.expander("AI selection rationale", expanded=False):
            if result.get("selection_rationale"):
                st.write(result["selection_rationale"])
            if result.get("selection_error"):
                st.warning(result["selection_error"])
            if result.get("selection_error_detail"):
                st.code(result["selection_error_detail"])

    st.subheader("5. Save to My Tours")
    render_save_to_my_tours(st.session_state["api_base_url"], get_access_token(), result, artist_label, artist_id)


def render_save_to_my_tours(api_base_url, token, result, artist_label, artist_id):
    schedule = result.get("schedule") or []
    if not schedule:
        st.info("Run optimization with a start date before saving a tour.")
        return

    tour_groups = st.session_state.get("tour_groups", [])
    artist_tour_groups = [tour for tour in tour_groups if tour.get("artist") == artist_id]
    selected_ids = result.get("selected_venue_ids", [])

    col1, col2 = st.columns([1, 1])
    with col1:
        save_mode = st.radio("Tour group", ["Create new", "Use existing"], horizontal=True)
        tour_id = None

        if save_mode == "Create new":
            default_name = f"{artist_label.split(' (ID ')[0]} Optimized Tour"
            tour_name = st.text_input("Tour name", value=default_name, key="save_tour_name")
            tour_description = st.text_area(
                "Description",
                value="Saved from the Streamlit optimizer demo.",
                key="save_tour_description",
            )
        else:
            if artist_tour_groups:
                tour_options = {
                    f"{tour.get('name', 'Tour')} (ID {tour['id']})": tour["id"]
                    for tour in artist_tour_groups
                }
                selected_tour_label = st.selectbox("Existing tour", options=list(tour_options.keys()))
                tour_id = tour_options[selected_tour_label]
            else:
                st.warning("No existing tour groups for this artist. Use Create new.")

    with col2:
        conflict_label = st.selectbox(
            "If saved dates conflict",
            ["Stop and show conflicts", "Skip conflicting dates", "Overwrite conflicting dates"],
        )
        conflict_map = {
            "Skip conflicting dates": "skip",
            "Overwrite conflicting dates": "overwrite",
        }

    can_save = save_mode == "Create new" or tour_id is not None
    if st.button("Save schedule", type="primary", disabled=not can_save):
        try:
            if save_mode == "Create new":
                created_tour = create_tour_group(
                    api_base_url,
                    token,
                    {
                        "artist": artist_id,
                        "name": tour_name,
                        "start_date": schedule[0]["date"],
                        "end_date": schedule[-1]["date"],
                        "description": tour_description,
                        "venue_ids": selected_ids,
                    },
                )
                tour_id = created_tour["id"]

            payload = {
                "artist_id": artist_id,
                "tour_id": tour_id,
                "schedule": schedule,
            }
            if conflict_label in conflict_map:
                payload["conflict_strategy"] = conflict_map[conflict_label]

            save_result = confirm_optimization(api_base_url, token, payload)
            refresh_account_data()
            st.success("Saved to My Tours")
            st.json(save_result)
        except requests.RequestException as error:
            display_error(error)


def render_my_tours_tab():
    if not require_login():
        return

    st.subheader("My Tours")
    if st.button("Refresh My Tours"):
        try:
            refresh_account_data()
            st.success("My Tours refreshed")
        except requests.RequestException as error:
            display_error(error)

    tour_groups = st.session_state.get("tour_groups", [])
    tour_dates = st.session_state.get("tour_dates", [])

    c1, c2 = st.columns(2)
    c1.metric("Tour groups", len(tour_groups))
    c2.metric("Saved tour dates", len(tour_dates))

    group_tab, date_tab = st.tabs(["Tour Groups", "Tour Dates"])
    with group_tab:
        if tour_groups:
            st.dataframe(tour_group_rows(tour_groups), use_container_width=True, hide_index=True)
        else:
            st.info("No tour groups yet.")
    with date_tab:
        if tour_dates:
            st.dataframe(tour_date_rows(tour_dates), use_container_width=True, hide_index=True)
        else:
            st.info("No saved tour dates yet.")


def render_venues_tab():
    if not require_login():
        return

    st.subheader("Venues")
    venues = st.session_state.get("venues", [])
    filtered_venues = render_venue_filters(venues, "venues")
    rows = [
        {
            "venue": venue.get("name", ""),
            "city": venue_city_name(venue) or venue.get("city", ""),
            "country": venue_country(venue) or "",
            "capacity": venue.get("capacity", ""),
            "operating_cost": venue.get("operating_cost", ""),
            "default_ticket_price": venue.get("default_ticket_price", ""),
            "venue_id": venue.get("id"),
        }
        for venue in filtered_venues
    ]
    if rows:
        st.dataframe(rows, use_container_width=True, hide_index=True)
    else:
        st.info("No venues match the selected filters.")


def render_methodology_tab():
    st.subheader("Calculation Methodology")
    st.caption("These notes summarize the backend logic used by the optimizer.")

    overview_rows = [
        {
            "area": "Distance",
            "method": "Uses the Haversine formula between venue latitude/longitude pairs.",
        },
        {
            "area": "Baseline route",
            "method": "Uses the selected venue order after optional max venue filtering.",
        },
        {
            "area": "Optimized route",
            "method": "Builds a nearest-neighbor route from the start venue, then improves it with 2-opt swaps.",
        },
        {
            "area": "Revenue",
            "method": "Estimates venue revenue from expected attendance times ticket price.",
        },
        {
            "area": "Cost",
            "method": "Adds travel cost and venue operating cost.",
        },
        {
            "area": "ROI",
            "method": "Calculates profit divided by total cost.",
        },
    ]
    st.dataframe(overview_rows, use_container_width=True, hide_index=True)

    formula_rows = [
        {
            "metric": "Expected attendance",
            "formula": "min(fan_count * engagement_score, venue_capacity)",
        },
        {
            "metric": "Venue revenue",
            "formula": "expected_attendance * ticket_price",
        },
        {
            "metric": "Route distance",
            "formula": "sum(Haversine distance between each consecutive venue)",
        },
        {
            "metric": "Travel cost",
            "formula": "cost_per_km * optimized_distance_km",
        },
        {
            "metric": "Total cost",
            "formula": "travel_cost + sum(venue.operating_cost)",
        },
        {
            "metric": "Route score",
            "formula": "(revenue_weight * revenue) - (distance_weight * distance)",
        },
        {
            "metric": "Distance saved",
            "formula": "(baseline_distance - optimized_distance) / baseline_distance * 100",
        },
        {
            "metric": "ROI",
            "formula": "(estimated_revenue - total_cost) / total_cost",
        },
    ]
    st.subheader("Formulas")
    st.dataframe(formula_rows, use_container_width=True, hide_index=True)

    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Venue Selection")
        st.markdown(
            """
- Country and city filters narrow the candidate venues before optimization.
- If `max_venues` is lower than the selected venue count, the backend selects a subset.
- Heuristic selection keeps the start venue, prefers a matching start city, then ranks by estimated revenue.
- AI venue selection can replace that subset when enabled and available; otherwise the heuristic path is used.
            """.strip()
        )

    with col2:
        st.subheader("Schedule")
        st.markdown(
            """
- Schedule dates follow the optimized route order.
- `min_gap_days` enforces the minimum spacing between shows.
- `travel_speed_km_per_day` adds extra travel days when distance requires it.
- Saved tour dates use the generated schedule returned by the API.
            """.strip()
        )

    with st.expander("Revenue inputs and fallbacks"):
        st.markdown(
            """
The revenue estimate starts from fan demand records for the artist and venue. Ticket price uses the first available value from fan demand, the venue default ticket price, the artist's latest saved tour date ticket price, then `0`.
            """.strip()
        )


init_state()
render_sidebar()

st.title("AI-Assisted Artist Tour Optimization Platform")
st.markdown(
    "Optimize multi-city artist tours using deterministic route optimization, "
    "AI-assisted venue selection, and revenue-aware scheduling."
)
col1, col2, col3 = st.columns(3)
col1.metric("Optimization Engine", "2-opt + NN")
col2.metric("AI Layer", "GPT-4.1-mini")
col3.metric("Deployment", "Railway + Streamlit")
st.divider()

account_tab, optimize_tab, my_tours_tab, venues_tab, methodology_tab = st.tabs(
    ["Account", "Optimize", "My Tours", "Venues", "Methodology"]
)

with account_tab:
    render_account_tab()

with optimize_tab:
    render_optimize_tab()

with my_tours_tab:
    render_my_tours_tab()

with venues_tab:
    render_venues_tab()

with methodology_tab:
    render_methodology_tab()
