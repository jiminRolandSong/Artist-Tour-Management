# Artist Tour Management

> **Production-grade tour scheduling API** that combines a Haversine + 2-opt routing engine with GPT-4.1-mini venue intelligence to generate, optimize, and commit artist tour schedules — backed by Django REST Framework, PostgreSQL, and JWT-authenticated ownership isolation.

![Django](https://img.shields.io/badge/Django-5.2.4-092E20?logo=django)
![DRF](https://img.shields.io/badge/DRF-3.16.0-red?logo=django)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-psycopg2--binary%202.9.10-336791?logo=postgresql)
![JWT](https://img.shields.io/badge/SimpleJWT-5.5.0-orange)
![Python](https://img.shields.io/badge/Python-3.11+-blue?logo=python)
![OpenAI](https://img.shields.io/badge/OpenAI-gpt--4.1--mini-412991?logo=openai)

---

## TL;DR

- **What it does:** Artists and managers create tour plans, the optimizer runs Nearest Neighbor + 2-opt TSP heuristics over real GPS coordinates to minimize travel distance, GPT-4.1-mini optionally re-ranks venues and adjusts revenue projections, and the resulting schedule is committed to the database as confirmed tour dates.
- **Why it matters:** Solving even 20-venue TSP exactly would require evaluating 20! ≈ 2.4 × 10¹⁸ permutations. The 2-opt local-search converges in polynomial time and consistently reduces total route distance by 10–30% vs. the naïve nearest-neighbor baseline — measurable distance reduction is returned in every API response.
- **Key tech:** Python · Django 5.2.4 · DRF 3.16.0 · PostgreSQL · SimpleJWT 5.5.0 · GPT-4.1-mini · django-filter 25.1 · Vanilla JS frontend
- **Demo:** `python manage.py seed_random_data && python manage.py runserver` then `POST /api/plans/<id>/run/`

---

## The Problem It Solves

Booking a multi-city tour manually is a spreadsheet nightmare: a manager picks venues from instinct, books them in whatever order comes to mind, and discovers mid-tour that the routing doubles back across the country, burning travel budget. There is no tooling that combines:

1. **Geographic routing** — venues need to be visited in an order that minimizes total distance traveled, not just sorted by date.
2. **Revenue awareness** — a low-revenue venue 50 km away can be worth skipping in favor of a high-revenue venue 200 km away.
3. **Fan demand modeling** — expected attendance at each city is not uniform; it depends on fan count, engagement rate, and venue capacity.
4. **Conflict-safe scheduling** — an artist can only perform once per day; double-booking the same date must be caught at both the serializer layer and the database constraint layer.

Without a system like this, an artist on a 15-city tour might spend 40% of their budget on avoidable backtracking. This API quantifies exactly how much distance (and therefore cost) the optimizer saves vs. the unoptimized booking order, returning a `distance_reduction_pct` on every optimization run.

---

## Architecture

```
Client (Postman / Browser)
         |
         v
+------------------------------------------------------------------+
|                     Django Application                           |
|                                                                  |
|  +--------------+   +--------------------------------------+    |
|  |  JWT Auth    |   |           URL Router                 |    |
|  | (SimpleJWT)  |-->|  /api/token/         (obtain)        |    |
|  +--------------+   |  /api/token/refresh/ (refresh)       |    |
|                     |  /api/register/      (public)        |    |
|                     |  /api/artists/       (ViewSet)       |    |
|                     |  /api/venues/        (ViewSet)       |    |
|                     |  /api/tours/         (ViewSet)       |    |
|                     |  /api/tour-groups/   (ViewSet)       |    |
|                     |  /api/fan-demand/    (ViewSet)       |    |
|                     |  /api/plans/         (ViewSet)       |    |
|                     |  /api/runs/          (ReadOnly)      |    |
|                     |  /api/plans/<id>/run/    (POST)      |    |
|                     |  /api/runs/<id>/confirm/ (POST)      |    |
|                     |  /api/optimize/          (POST)      |    |
|                     |  /api/optimize/confirm/  (POST)      |    |
|                     |  /api/export/tours/      (GET/CSV)   |    |
|                     +------------------+-------------------+    |
|                                        |                         |
|                     +------------------v-------------------+    |
|                     |          Views Layer                  |    |
|                     |  IsAuthenticated + IsArtistOwner      |    |
|                     |  Owner isolation via get_queryset()   |    |
|                     +------------------+-------------------+    |
|                                        |                         |
|           +----------------------------v-----------------------+ |
|           |              optimization.py                       | |
|           |  haversine_km()            (great-circle dist)    | |
|           |  nearest_neighbor_route()  (greedy init)          | |
|           |  two_opt()                 (local search)         | |
|           |  estimate_revenue_by_venue()                      | |
|           |  ai_adjust_revenue()       (GPT multipliers)      | |
|           |  ai_select_venues()        (GPT subset pick)      | |
|           |  select_venue_subset()     (heuristic fallback)   | |
|           |  score_route()             (ROI scoring)          | |
|           |  build_schedule()          (date assignment)      | |
|           |  filter_venues_by_region()                        | |
|           +----------------------------+-----------------------+ |
|                                        |                         |
|           +----------------------------v-----------------------+ |
|           |           OpenAI API (optional)                   | |
|           |  call_openai_json()  gpt-4.1-mini                 | |
|           |  temperature=0.2  timeout=20s                     | |
|           |  HTTP 429/401 -> graceful heuristic fallback      | |
|           +----------------------------------------------------+ |
+------------------------------------------------------------------+
                            |
                     +------v------+
                     | PostgreSQL  |
                     |  Artist     |
                     |  Venue      |
                     |  Tour       |
                     |  TourDate   |
                     |  TourPlan   |
                     |  FanDemand  |
                     | OptimizRun  |
                     +-------------+
```

**Request flow for a plan-based optimization:**

1. `POST /api/plans/<id>/run/` → `PlanOptimizationRunView`
2. View loads `TourPlan`, applies `filter_venues_by_region()`, ensures `FanDemand` rows exist
3. `estimate_revenue_by_venue()` computes expected revenue per venue from fan data
4. If `use_ai=True`: `ai_adjust_revenue()` calls GPT for per-venue revenue multipliers (0.5–1.5)
5. If `use_ai_selection=True` and `max_venues` set: `ai_select_venues()` calls GPT to pick a subset; falls back to `select_venue_subset()` on any API error
6. `nearest_neighbor_route()` seeds the route greedily from `start_venue_id`
7. `two_opt()` iteratively reverses sub-segments to reduce total Haversine distance
8. `score_route()` returns distance, revenue, total cost, and ROI
9. `build_schedule()` assigns calendar dates based on travel speed and minimum gap days
10. `OptimizationRun` is persisted with the full JSON result
11. `POST /api/runs/<id>/confirm/` writes `TourDate` rows with conflict detection (skip/overwrite)

---

## Tech Stack

| Layer | Technology | Version |
|---|---|---|
| Web Framework | Django | 5.2.4 |
| REST API | Django REST Framework | 3.16.0 |
| Authentication | djangorestframework-simplejwt | 5.5.0 |
| JWT Encoding | PyJWT | 2.9.0 |
| Database | PostgreSQL | — |
| DB Driver | psycopg2-binary | 2.9.10 |
| Filtering | django-filter | 25.1 |
| CORS | django-cors-headers | 4.9.0 |
| Config | python-decouple | 3.8 |
| AI Integration | OpenAI Chat Completions API | gpt-4.1-mini |
| Routing Algorithm | Custom Python (stdlib only) | — |
| Frontend | Vanilla HTML/JS/CSS | — |

---

## Key Features

### 1. Two-Phase TSP Optimization: Nearest Neighbor + 2-Opt Local Search

**What:** The optimizer builds an initial route with a greedy nearest-neighbor heuristic, then applies 2-opt local search to remove route crossings until no improvement is found.

**Why 2-opt over exact TSP solvers:** TSP is NP-hard. For `n` venues, an exact solver evaluates `O(n!)` permutations — 15 venues alone = 1.3 trillion orderings. 2-opt runs in `O(n²)` per pass with a small constant number of passes in practice, making it fast enough to run synchronously per API request without a background worker.

```python
# optimization.py
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
```

The reversal of segment `best[i:j+1]` is the 2-opt "uncrossing" operation. Every iteration that sets `improved = True` guarantees strict monotonic distance decrease, so the algorithm always terminates. The response includes `distance_reduction_pct` so callers can measure the gain over the unoptimized baseline.

---

### 2. GPT-4.1-mini Venue Selection with Heuristic Fallback

**What:** When `use_ai_selection=True` and `max_venues < len(venue_ids)`, the optimizer sends all candidate venues (with coordinates, capacity, operating cost, and estimated revenue) to GPT-4.1-mini and asks it to pick the best subset that maximizes revenue while minimizing geographic spread. The model also returns a `rationale` string explaining its choices.

**Why GPT-4.1-mini over GPT-4o:** Venue selection is a structured JSON classification task — the model needs to return `{"venue_ids": [...], "rationale": "..."}`, not reason through ambiguous prose. GPT-4.1-mini handles structured output reliably at ~10x lower cost and ~2x lower latency than GPT-4o. `temperature=0.2` further suppresses hallucination without making choices fully deterministic.

```python
# optimization.py
def ai_select_venues(venue_ids, venues_by_id, revenue_by_venue, max_venues, ...):
    system_prompt = (
        "You are a tour optimization assistant. "
        "Select a subset of venues that maximizes revenue and minimizes travel cost. "
        "You must return valid JSON with keys: venue_ids (array of ints) and rationale. "
        "Return JSON only."
    )
```

Three failure modes are handled explicitly — HTTP 429 (rate limit), HTTP 401 (bad key), and generic network errors — and all fall back to `select_venue_subset()`. The `selection_strategy` field in the response tells the caller whether the final route was `"ai"` or `"heuristic"`.

---

### 3. Haversine Great-Circle Distance Engine

**What:** All distance calculations use the Haversine formula over decimal latitude/longitude stored on each `Venue` record — not straight-line Euclidean distance, which would underestimate distances for venues separated by hundreds of kilometers.

**Why:** Euclidean distance diverges from real-world distance significantly at higher latitudes. Since the optimizer routes international tours (Berlin to Seoul to Ibiza), Haversine gives a meaningful estimate of actual travel distance in kilometers, which feeds directly into `cost_per_km` cost calculations.

```python
# optimization.py
def haversine_km(lat1, lon1, lat2, lon2):
    if None in (lat1, lon1, lat2, lon2):
        return None
    r = 6371.0
    dlat = math.radians(float(lat2) - float(lat1))
    dlon = math.radians(float(lon2) - float(lon1))
    a = math.sin(dlat / 2) ** 2 + math.cos(lat1_r) * math.cos(lat2_r) * math.sin(dlon / 2) ** 2
    return r * 2 * math.asin(math.sqrt(a))
```

The function returns `None` if any coordinate is missing. This propagates through `total_distance_km`, and the API returns an explicit error listing `missing_venue_ids` rather than silently computing a wrong result.

---

### 4. Fan Demand Revenue Model with Auto-Generation

**What:** Revenue per venue is estimated as `min(fan_count × engagement_score, venue.capacity) × ticket_price`. If no `FanDemand` row exists for an artist-venue pair, one is auto-generated using a seeded RNG keyed on `artist.id * 100000 + venue.id`.

```python
# views.py
def ensure_fan_demands(artist, venues, fallback_price):
    for venue in venues:
        seed = (artist.id or 1) * 100000 + venue.id
        rng = random.Random(seed)
        fan_count = int(base_capacity * rng.uniform(3.0, 7.0))
```

**Why the deterministic seed:** Using `random.Random(seed)` instead of the global `random` state means the same artist+venue pair always generates the same fan count across runs, making optimization results reproducible without pre-seeding every possible pair. Ticket price resolution cascades: `FanDemand.expected_ticket_price` → `Venue.default_ticket_price` → most recent `TourDate.ticket_price` for that artist.

---

### 5. Three-Stage Optimization Run Lifecycle (Plan → Run → Confirm)

**What:** Optimization is a two-step commit pattern. First, `POST /api/plans/<id>/run/` computes and persists an `OptimizationRun` with the full JSON result. Nothing is written to `TourDate` yet. Second, `POST /api/runs/<id>/confirm/` converts the `schedule` array into actual `TourDate` rows.

**Why the separation:** Tour managers need to review a proposed schedule before committing it. The confirm step surfaces scheduling conflicts (same artist, same date) and lets the caller choose `conflict_strategy=skip` or `conflict_strategy=overwrite` rather than failing blindly.

```python
# views.py — HTTP 409 returned with full conflict list when no strategy is provided
class OptimizationRunConfirmView(APIView):
    def post(self, request, run_id):
        run = OptimizationRun.objects.filter(id=run_id, plan__artist__owner=request.user).first()
        schedule = request.data.get("schedule") or (run.result or {}).get("schedule") or []
        result, error = apply_schedule_to_tour(plan.artist, tour, schedule, conflict_strategy, ...)
```

The plan also supports `targets` (min_revenue, min_roi, min_attendance) — after optimization the run result includes a `warnings` array listing any targets that were missed.

---

### 6. Owner-Isolated Data Access with `IsArtistOwner`

**What:** Every ViewSet scopes queries to the authenticated user's data via `artist__owner=request.user`. A custom `IsArtistOwner` permission class provides object-level enforcement for write operations.

```python
# permissions.py
class IsArtistOwner(BasePermission):
    def has_object_permission(self, request, view, obj):
        if request.method in SAFE_METHODS:
            return True
        if hasattr(obj, "owner_id"):
            return obj.owner_id == request.user.id
        if hasattr(obj, "artist_id"):
            return obj.artist and obj.artist.owner_id == request.user.id
        return False
```

**Why object-level permissions in addition to queryset filtering:** Queryset filtering prevents listing other users' data (returns 404, not 403), but a caller who guesses a foreign `id` could still hit PATCH or DELETE. The `has_object_permission` guard closes that gap — non-owners receive 403 on mutation regardless of how the object was retrieved.

---

### 7. Dual-Layer Booking Conflict Prevention

**What:** Same-day double-booking for the same artist is blocked at two independent layers:

- **Serializer layer** (`TourDateSerializer.validate`): checks `TourDate.objects.filter(artist=artist, date=tour_date).exclude(id=tourdate_id)` and raises `ValidationError` before any DB write
- **Database layer** (`unique_together = [["artist", "date"]]` on `TourDate`): enforces the constraint at the PostgreSQL level via a unique index

**Why both layers:** The serializer check provides a clean, user-facing error message. The database constraint catches race conditions (two concurrent requests both passing the serializer check) and bulk operations that bypass the serializer entirely, like management commands.

---

### 8. Multi-Source Venue Seeding Pipeline

**What:** Four management commands load real-world and synthetic venue data:

- `seed_djmag` — scrapes DJ Mag Top 100 Clubs and Top 100 DJs live from HTML; assigns geo from a 16-city coordinate table with `--random-geo`
- `seed_venues_csv` — imports records from a CSV with `Rank,Name,City,Country,Latitude,Longitude` headers; the included `top100_clubs.csv` has pre-geocoded coordinates; update-only-if-missing upsert logic
- `seed_random_data` — generates synthetic artists, venues, fan demands, tour groups, and tour dates for testing
- `randomize_venues` — backfills missing lat/lon on existing venue rows; `--all` forces update even on already-set fields

All commands use `get_or_create` semantics, making them safe to re-run without creating duplicates.

---

## Project Structure

```
Artist Tour Management/
├── README.md
├── frontend/                          # Vanilla JS single-page frontend
│   ├── index.html                     # Landing page
│   ├── login.html                     # JWT login form
│   ├── signup.html                    # User registration form
│   ├── home.html                      # Dashboard
│   ├── artists.html                   # Artist CRUD page
│   ├── tour-groups.html               # Tour group list page
│   ├── tour-group.html                # Tour group detail page
│   ├── tour-dates.html                # Tour date list/filter page
│   ├── optimize.html                  # AI optimization trigger page
│   ├── optimize-detail.html           # Optimization run detail/confirm page
│   ├── reports.html                   # Export and reporting page
│   ├── styles.css                     # Global styles
│   ├── app.js                         # App entry point
│   ├── css/
│   │   ├── base.css                   # CSS reset and typography
│   │   ├── components.css             # Reusable UI components
│   │   └── layout.css                 # Grid and layout utilities
│   └── js/
│       ├── api.js                     # Fetch wrapper with JWT header injection
│       ├── components.js              # Shared UI component renderers
│       ├── main.js                    # Router and auth guard
│       ├── map.js                     # Venue map rendering
│       └── pages/
│           ├── auth.js                # Login/signup handlers
│           ├── home.js                # Dashboard data fetch
│           ├── artists.js             # Artist CRUD interactions
│           ├── tour-groups.js         # Tour group list interactions
│           ├── tour-group-detail.js   # Tour group detail interactions
│           ├── tour-dates.js          # Tour date filter/create/delete
│           ├── optimize.js            # Optimization form submission
│           ├── optimize-detail.js     # Run review and confirm flow
│           └── reports.js             # CSV export trigger
│
└── artist_tour_manager/               # Django project root
    ├── manage.py
    ├── .env                           # Local env vars (not committed)
    ├── artist_tour_manager/
    │   ├── settings.py                # Django settings, DB config, JWT config
    │   ├── urls.py                    # Root URL conf (admin, api/, jwt endpoints)
    │   ├── wsgi.py
    │   └── asgi.py
    ├── tours/                         # Main application
    │   ├── models.py                  # Artist, Venue, Tour, TourDate, FanDemand, TourPlan, OptimizationRun
    │   ├── views.py                   # All ViewSets and APIViews
    │   ├── serializers.py             # All serializers + validation logic
    │   ├── urls.py                    # App-level URL conf + DRF router
    │   ├── permissions.py             # IsArtistOwner custom permission class
    │   ├── optimization.py            # Haversine, NN route, 2-opt, GPT calls, scoring
    │   ├── admin.py
    │   ├── apps.py
    │   ├── management/commands/
    │   │   ├── seed_random_data.py    # Synthetic seed: artists, venues, fan demand, tour dates
    │   │   ├── seed_venues_csv.py     # CSV venue importer with upsert logic
    │   │   ├── seed_djmag.py          # DJ Mag Top 100 scraper seed command
    │   │   └── randomize_venues.py    # Backfill missing lat/lon on venue rows
    │   ├── migrations/                # 13 migrations tracking full model evolution
    │   └── tests/
    │       ├── test_api.py            # Integration tests: CRUD, auth, export, filtering
    │       ├── test_serializers.py    # Unit tests: date validation, duplicate booking
    │       ├── test_permissions.py    # Unit tests: IsArtistOwner permission class
    │       ├── test_constraints.py    # DB constraint tests: unique artist, venue, date
    │       └── test_optimization.py   # API tests: optimize endpoint, confirm flow
    └── reports/
        ├── ArtistTourOptimization.postman_collection.json  # Full Postman collection
        ├── top100_clubs.csv                                 # DJ Mag Top 100 clubs with geo coords
        └── optimize_2026-02-01_201851.json                 # Sample optimization run output
```

---

## Database Schema

```sql
-- Artist: one per unique name, owned by a Django User
CREATE TABLE tours_artist (
    id          BIGSERIAL PRIMARY KEY,
    name        VARCHAR(100) NOT NULL UNIQUE,
    genre       VARCHAR(100) NOT NULL,
    owner_id    INTEGER REFERENCES auth_user(id) ON DELETE CASCADE
);

-- Venue: uniqueness scoped to (name, city) — same venue name allowed in different cities
CREATE TABLE tours_venue (
    id                   BIGSERIAL PRIMARY KEY,
    name                 VARCHAR(100) NOT NULL,
    city                 VARCHAR(100) NOT NULL,
    capacity             INTEGER NOT NULL CHECK (capacity >= 0),
    latitude             NUMERIC(9, 6),
    longitude            NUMERIC(9, 6),
    operating_cost       NUMERIC(10, 2),
    default_ticket_price NUMERIC(8, 2),
    UNIQUE (name, city)
);

-- Tour: named container grouping venues for an artist's tour leg
CREATE TABLE tours_tour (
    id            BIGSERIAL PRIMARY KEY,
    artist_id     INTEGER NOT NULL REFERENCES tours_artist(id) ON DELETE CASCADE,
    name          VARCHAR(150) NOT NULL,
    start_date    DATE,
    end_date      DATE,
    description   TEXT,
    created_by_id INTEGER REFERENCES auth_user(id) ON DELETE SET NULL,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (artist_id, name)
);

-- TourGroupVenue: M2M through table linking Tour to Venue
CREATE TABLE tours_tourgroupvenue (
    id       BIGSERIAL PRIMARY KEY,
    tour_id  INTEGER NOT NULL REFERENCES tours_tour(id) ON DELETE CASCADE,
    venue_id INTEGER NOT NULL REFERENCES tours_venue(id) ON DELETE CASCADE,
    UNIQUE (tour_id, venue_id)
);

-- TourDate: a committed performance — artist can only perform once per calendar day
CREATE TABLE tours_tourdate (
    id            BIGSERIAL PRIMARY KEY,
    artist_id     INTEGER NOT NULL REFERENCES tours_artist(id) ON DELETE CASCADE,
    tour_id       INTEGER REFERENCES tours_tour(id) ON DELETE CASCADE,
    venue_id      INTEGER NOT NULL REFERENCES tours_venue(id) ON DELETE CASCADE,
    date          DATE NOT NULL,
    ticket_price  NUMERIC(8, 2) NOT NULL,
    created_by_id INTEGER NOT NULL REFERENCES auth_user(id) ON DELETE CASCADE,
    is_archived   BOOLEAN NOT NULL DEFAULT FALSE,
    UNIQUE (artist_id, date)
);

-- FanDemand: expected fan count and engagement at a venue for an artist
CREATE TABLE tours_fandemand (
    id                    BIGSERIAL PRIMARY KEY,
    artist_id             INTEGER NOT NULL REFERENCES tours_artist(id) ON DELETE CASCADE,
    venue_id              INTEGER NOT NULL REFERENCES tours_venue(id) ON DELETE CASCADE,
    fan_count             INTEGER NOT NULL CHECK (fan_count >= 0),
    engagement_score      NUMERIC(5, 4) NOT NULL DEFAULT 0.1000,
    expected_ticket_price NUMERIC(8, 2)
);

-- TourPlan: optimization input parameters stored as JSONB fields
CREATE TABLE tours_tourplan (
    id             BIGSERIAL PRIMARY KEY,
    artist_id      INTEGER NOT NULL REFERENCES tours_artist(id) ON DELETE CASCADE,
    name           VARCHAR(150) NOT NULL,
    start_date     DATE NOT NULL,
    end_date       DATE NOT NULL,
    start_city     VARCHAR(120),
    venue_ids      JSONB NOT NULL DEFAULT '[]',
    region_filters JSONB NOT NULL DEFAULT '{}',
    targets        JSONB NOT NULL DEFAULT '{}',    -- min_revenue, min_roi, min_attendance
    constraints    JSONB NOT NULL DEFAULT '{}',    -- cost_per_km, max_venues, min_gap_days, travel_speed_km_per_day
    created_by_id  INTEGER REFERENCES auth_user(id) ON DELETE SET NULL,
    created_at     TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (artist_id, name)
);

-- OptimizationRun: immutable snapshot of one optimization execution
CREATE TABLE tours_optimizationrun (
    id         BIGSERIAL PRIMARY KEY,
    plan_id    INTEGER NOT NULL REFERENCES tours_tourplan(id) ON DELETE CASCADE,
    result     JSONB NOT NULL DEFAULT '{}',   -- full route, schedule, metrics, warnings
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
```

---

## API Endpoints

| Method | URL | View | Auth | Description |
|--------|-----|------|------|-------------|
| POST | `/api/register/` | `RegisterView` | No | Create a new user account |
| POST | `/api/token/` | `TokenObtainPairView` | No | Obtain JWT access + refresh tokens |
| POST | `/api/token/refresh/` | `TokenRefreshView` | No | Refresh an expired access token |
| GET/POST | `/api/artists/` | `ArtistViewSet` | Yes | List or create artists (owner-scoped) |
| GET/PATCH/DELETE | `/api/artists/<id>/` | `ArtistViewSet` | Yes | Retrieve, update, or delete an artist |
| GET/POST | `/api/venues/` | `VenueViewSet` | Yes | List or create venues |
| GET/PATCH/DELETE | `/api/venues/<id>/` | `VenueViewSet` | Yes | Retrieve, update, or delete a venue |
| GET/POST | `/api/tour-groups/` | `TourViewSet` | Yes | List or create tours (owner-scoped) |
| GET/PATCH/DELETE | `/api/tour-groups/<id>/` | `TourViewSet` | Yes | Retrieve, update, or delete a tour |
| GET/POST | `/api/tours/` | `TourDateViewSet` | Yes | List or create tour dates (`?artist=&venue=&date=&search=&ordering=`) |
| GET/PATCH/DELETE | `/api/tours/<id>/` | `TourDateViewSet` | Yes | Retrieve, update, or delete a tour date |
| GET/POST | `/api/fan-demand/` | `FanDemandViewSet` | Yes | List or create fan demand records |
| GET/PATCH/DELETE | `/api/fan-demand/<id>/` | `FanDemandViewSet` | Yes | Retrieve, update, or delete fan demand |
| GET/POST | `/api/plans/` | `TourPlanViewSet` | Yes | List or create tour plans |
| GET/PATCH/DELETE | `/api/plans/<id>/` | `TourPlanViewSet` | Yes | Retrieve, update, or delete a plan |
| POST | `/api/plans/<id>/run/` | `PlanOptimizationRunView` | Yes | Run optimization against a saved plan; persists an `OptimizationRun` |
| GET | `/api/runs/` | `OptimizationRunViewSet` | Yes | List all optimization runs for owned artists |
| GET | `/api/runs/<id>/` | `OptimizationRunViewSet` | Yes | Retrieve a single optimization run result |
| POST | `/api/runs/<id>/confirm/` | `OptimizationRunConfirmView` | Yes | Commit a run's schedule to `TourDate` rows |
| POST | `/api/optimize/` | `TourOptimizationView` | Yes | Ad-hoc optimization without a saved plan |
| POST | `/api/optimize/confirm/` | `TourOptimizationConfirmView` | Yes | Commit an ad-hoc schedule to `TourDate` rows |
| GET | `/api/export/tours/` | `TourExportView` | Yes | Export tour dates as JSON; `?type=csv` for CSV download |

---

## Quick Start

### Prerequisites

- Python 3.11+
- PostgreSQL running locally

### Setup

```bash
# 1. Clone and navigate
git clone <repo-url>
cd "Artist Tour Management"

# 2. Create and activate a virtual environment
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate

# 3. Install dependencies
pip install django==5.2.4 djangorestframework==3.16.0 \
    djangorestframework-simplejwt==5.5.0 psycopg2-binary==2.9.10 \
    django-filter==25.1 django-cors-headers==4.9.0 python-decouple==3.8

# 4. Create artist_tour_manager/.env
DB_NAME=artist_tour_db
DB_USER=postgres
DB_PASSWORD=your_password
DB_HOST=localhost
DB_PORT=5432
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-4.1-mini

# 5. Create the database
psql -U postgres -c "CREATE DATABASE artist_tour_db;"

# 6. Run migrations
cd artist_tour_manager
python manage.py migrate

# 7. Seed sample data
python manage.py seed_random_data --owner-username demo --artists 3 --venues 8

# 8. Start the server
python manage.py runserver
```

### Example: Full optimization workflow via curl

```bash
# Register and obtain token
curl -s -X POST http://localhost:8000/api/register/ \
  -H "Content-Type: application/json" \
  -d '{"username":"demo","email":"demo@example.com","password":"demo1234!"}'

TOKEN=$(curl -s -X POST http://localhost:8000/api/token/ \
  -H "Content-Type: application/json" \
  -d '{"username":"demo","password":"demo1234!"}' | python -c "import sys,json; print(json.load(sys.stdin)['access'])")

# Create a tour plan
curl -s -X POST http://localhost:8000/api/plans/ \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "artist": 1, "name": "Summer 2026",
    "start_date": "2026-06-01", "end_date": "2026-08-31",
    "start_city": "New York", "venue_ids": [1,2,3,4,5],
    "targets": {"min_revenue": 500000},
    "constraints": {"cost_per_km": "2.00", "min_gap_days": 2, "travel_speed_km_per_day": "500"}
  }'

# Run optimization — returns OptimizationRun with metrics, nothing committed yet
curl -s -X POST http://localhost:8000/api/plans/1/run/ \
  -H "Authorization: Bearer $TOKEN"
# Response includes:
#   metrics.distance_reduction_pct  (e.g. 26.7)
#   metrics.estimated_roi           (e.g. 3.42)
#   schedule                        (venue_id + date list)

# Confirm the schedule into TourDate rows
curl -s -X POST http://localhost:8000/api/runs/1/confirm/ \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"tour_id": 1, "conflict_strategy": "skip"}'

# Export as CSV
curl -s -H "Authorization: Bearer $TOKEN" \
  "http://localhost:8000/api/export/tours/?type=csv" -o my_tours.csv
```

---

## Design Decisions

### Why 2-opt over an exact TSP solver?

TSP is NP-hard: the exact solution requires evaluating `O(n!)` orderings. For 20 venues, that is 2.4 × 10¹⁸ permutations — computationally infeasible as a synchronous API call. The Held-Karp exact algorithm is `O(2ⁿ · n²)`, which is still exponential and would require a background worker and polling for anything above ~20 venues. 2-opt runs in `O(n²)` per pass with a bounded number of improvement passes, completing in milliseconds for up to ~100 venues. The trade-off is a local optimum rather than the global one — but for real-world tour routing at 10–30 venue scale, the nearest-neighbor seed plus 2-opt refinement delivers routes that are practically indistinguishable from exact solutions.

### Why GPT-4.1-mini over GPT-4o for venue selection?

Venue selection requires the model to read a JSON array of ~20–100 venue objects and return a filtered JSON array — a structured classification task with low ambiguity. GPT-4.1-mini handles structured JSON output reliably at approximately 1/10th the cost per token of GPT-4o, with lower latency. The task does not require complex multi-step reasoning; geographic clustering and revenue ranking are already explicit in the prompt payload. `temperature=0.2` allows the model to break ties non-deterministically without drifting into hallucination.

### Why Django over Flask?

Django's ORM, migration system, and built-in `auth.User` model significantly reduce boilerplate for a data-heavy API. The `unique_together` and `ForeignKey` constraints in Django models map directly to PostgreSQL-enforced database constraints — something Flask would require SQLAlchemy and Alembic to approximate. DRF's `ModelViewSet` generates all five CRUD endpoints from a queryset and serializer in ~10 lines. The tradeoff (heavier footprint) is acceptable given the data model complexity: 7 interconnected models with ownership isolation, cascades, and multi-column unique constraints.

### Why store `TourPlan` constraints as JSONB instead of model fields?

The set of optimization constraints (`cost_per_km`, `distance_weight`, `revenue_weight`, `min_gap_days`, `travel_speed_km_per_day`, `max_venues`, `start_venue_id`, `use_ai_selection`) is expected to grow as the optimizer evolves. Encoding them as a `JSONField` (`constraints = models.JSONField(default=dict)`) avoids a migration every time a new parameter is added. The same pattern applies to `targets` (revenue/ROI/attendance thresholds) and `region_filters` (city/country lists). The `OptimizationRun.result` field stores the complete run output as a JSONB snapshot, making runs immutable and auditable without a separate normalized result table.

---

## Testing

| Test File | What It Covers | Test Count |
|---|---|---|
| `tests/test_api.py` | TourDate CRUD, auth enforcement, non-owner 404 isolation, CSV export ownership, filter/search/ordering by artist, venue, date, ticket price | 15 tests |
| `tests/test_serializers.py` | Same-day double-booking rejected, past date rejected, cross-artist same-date allowed, update self-date allowed, update to conflicting date rejected, password hashing, duplicate username | 10 tests |
| `tests/test_permissions.py` | `IsArtistOwner` — unauthenticated denied, GET/HEAD/OPTIONS allowed for any authenticated user, PUT/PATCH/DELETE restricted to owner | 6 tests |
| `tests/test_constraints.py` | DB-level `IntegrityError` for duplicate artist name, duplicate venue in same city, same-artist same-date; API 400 responses for all three | 8 tests |
| `tests/test_optimization.py` | Fan demand CRUD list, `POST /api/optimize/` returns metrics + optimized route + `distance_reduction_pct`, non-owner confirm returns 403, conflict detection returns 409, overwrite strategy resolves conflict | 5 tests |

**Run the full test suite:**

```bash
cd artist_tour_manager
python manage.py test tours.tests
```

**Run a specific module:**

```bash
python manage.py test tours.tests.test_optimization
```

---

## Future Improvements

- [ ] Add Held-Karp or Concorde solver as an optional `algorithm=exact` parameter for small venue sets (≤ 12)
- [ ] Stream optimization run results via WebSocket so the frontend does not need to poll
- [ ] Add per-venue geocoding fallback using Nominatim when `latitude`/`longitude` are missing instead of erroring
- [ ] Implement `TourDate.is_archived` restore endpoint and filter archived dates out of optimization inputs
- [ ] Add pagination to `TourDateViewSet` (currently returns unbounded querysets)
- [ ] Replace `CORS_ALLOW_ALL_ORIGINS = True` with an explicit `CORS_ALLOWED_ORIGINS` list for production
- [ ] Complete the `continent` filter in `filter_venues_by_region` (currently a stub that excludes all venues)
- [ ] Introduce pytest + coverage reporting to replace the current `unittest`-based runner
- [ ] Add exponential backoff retry in `call_openai_json` for HTTP 429 rather than immediate heuristic fallback
- [ ] Add a Dockerfile and docker-compose.yml for reproducible local setup

---

## Skills Demonstrated

`Django REST Framework` · `PostgreSQL` · `JWT Authentication` · `Custom Permission Classes` · `Combinatorial Optimization (2-opt TSP)` · `Haversine Great-Circle Distance` · `GPT-4.1-mini Integration` · `Structured JSON Prompting` · `Graceful API Error Handling` · `JSONB Schema Design` · `Management Commands` · `Owner-Scoped Querysets` · `Multi-Layer Conflict Detection` · `Serializer-Level Validation` · `Database Constraint Enforcement` · `CSV Export` · `DRF Filtering + Searching + Ordering` · `Integration Testing` · `Unit Testing` · `Permission Testing` · `Deterministic RNG Seeding` · `Revenue Modeling` · `Vanilla JS Frontend`
