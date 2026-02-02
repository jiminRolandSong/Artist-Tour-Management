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

## Notes

- Tour plan names must be unique per artist.
- Plan dates must be in the future and end after start.

## License

MIT
