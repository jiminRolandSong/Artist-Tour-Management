# Artist Tour Manager

Full-stack tour management platform for artists and managers. Django REST API + lightweight HTML frontend for managing artists, venues, tour groups, and AI-optimized tour schedules.

## Features

- Owner-based authentication and permissions (JWT)
- Manage Artists, Venues, Tour Dates, and Tour Groups
- Tour Groups with assigned venues + start/end dates
- AI optimization flow (Plan -> Run -> Confirm)
- Conflict handling when confirming schedules (skip/overwrite)
- Archive/restore past tour dates
- CSV export of user-created tours
- Lightweight frontend (landing, login/signup, home, artists, tour groups, tour dates, AI optimize)

## Setup

1. **Clone the repository**

2. **Install dependencies**
   ```sh
   pip install -r requirements.txt
   ```

3. **Configure environment variables**

   Create a `.env` file in the root directory:
   ```
   DB_NAME=your_db_name
   DB_USER=your_db_user
   DB_PASSWORD=your_db_password
   DB_HOST=localhost
   DB_PORT=5432
   OPENAI_API_KEY=your_openai_api_key
   OPENAI_MODEL=gpt-4.1-mini
   ```

4. **Apply migrations**
   ```sh
   python manage.py migrate
   ```

5. **Run the development server**
   ```sh
   python manage.py runserver
   ```

## API Endpoints

- **Artists:** `/api/artists/`
- **Venues:** `/api/venues/`
- **Tour Dates:** `/api/tours/`
- **Tour Groups:** `/api/tour-groups/`
- **Plans:** `/api/plans/`
- **Plan Run:** `/api/plans/{id}/run/`
- **Run Confirm:** `/api/runs/{id}/confirm/`
- **Register:** `/api/register/`
- **Token:** `/api/token/`
- **Token Refresh:** `/api/token/refresh/`
- **Export Tours (CSV):** `/api/export/tours/?type=csv`
- **Optimize (Legacy):** `/api/optimize/`

## Filtering & Searching

- Filter tours by artist, venue, or date:
  ```
  /api/tours/?artist=1&venue=2&date=2025-09-01
  ```
- Search by artist or venue name:
  ```
  /api/tours/?search=Queen
  ```

## AI Optimization Workflow

1. Create a Tour Group and assign venues.
2. Set start/end dates for the Tour Group.
3. On the AI Optimize page, select the Tour Group and run optimization.
4. Confirm the schedule into Tour Dates (with conflict strategy).

## Frontend

Serve the frontend files from the `frontend/` folder (any static server works).
- `frontend/index.html` (landing)
- `frontend/login.html` / `frontend/signup.html`
- `frontend/home.html`
- `frontend/artists.html`
- `frontend/tour-groups.html`
- `frontend/tour-dates.html`
- `frontend/optimize.html`
- `frontend/reports.html`

## Export

Export your created tours as CSV:
```
GET /api/export/tours/?type=csv
```

## Testing

Run tests with:
```sh
python manage.py test
```

### Test Coverage Overview

- **API access & ownership:** unauthenticated access denied, owners can CRUD, non-owners blocked.
- **Business rules:** no same-day booking for same artist, past dates rejected.
- **Registration:** public registration, password hashing, duplicate username rejected.
- **Export & filters:** CSV export auth + ownership, filter/search/order endpoints.
- **Constraints:** unique artist name, unique venue per city, duplicate dates rejected at DB level.
- **Optimization flow:** fan demand CRUD, optimize returns metrics, confirm schedule permissions + conflicts.

## AI Optimization Logic (Current)

**Inputs (Plan):**
- `artist`, `name`, `start_date`, `end_date`
- `venue_ids` (selected venues to visit)
- `start_city` (and optional `start_venue_id`)
- `targets` (min revenue/ROI/attendance)
- `constraints` (min gap days, travel speed)

**Process:**
1. Create a **Tour Plan** for the selected tour group and venues.
2. Run optimization to produce an **optimized route** and a **schedule**.
3. Review/edit the schedule in the UI.
4. Confirm the run to create **Tour Dates**, with conflict strategy (`skip`/`overwrite`).

**Outputs (Run Result):**
- `optimized_route` (venue order)
- `schedule` (venue_id + date list)
- `metrics` (distance reduction %, estimated ROI)
- `warnings` (constraint violations or issues)

### Algorithm Notes

- **Distance model:** great-circle distance (Haversine) between venue lat/lon.
- **Baseline route:** nearest-neighbor route from `start_venue_id` (or first venue if none).
- **Route improvement:** 2-opt local search to reduce total distance.
- **Revenue estimation:** fan demand uses `expected_ticket_price` and `fan_count * engagement_score`.
- **AI adjustment (optional):** OpenAI can adjust per-venue revenue via multipliers (0.5–1.5) based on fan density + geographic clustering.
- **Scoring:** weighted revenue minus weighted distance, plus operating + travel cost accounting.
- **Scheduling:** builds dates by applying min gap days and travel time (distance / speed).
- **Region filters:** optional city/country/continent filtering before optimization (excluded venues reported).
- **Constraints enforced:** start venue lock, minimum gap days, travel speed limit (km/day).

## Notes

- Tour plan names must be unique per artist.
- Plan dates must be in the future and end after start.

## License

MIT
