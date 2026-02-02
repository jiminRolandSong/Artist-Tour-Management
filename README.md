# Artist Tour Manager

A Django REST API for managing artists, venues, and tour dates. Includes user registration, JWT authentication, filtering, searching, ordering, and CSV export of user-created tours.

## Features

- Manage Artists, Venues, and Tour Dates
- User registration endpoint
- JWT authentication (`/api/token/`)
- Permissions: Only owners can modify their tours
- Filtering, searching, and ordering for tours
- Export user tours to CSV
- AI-assisted tour route optimization with ROI estimates

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
- **Tours:** `/api/tours/`
- **Register:** `/api/register/`
- **Token:** `/api/token/`
- **Token Refresh:** `/api/token/refresh/`
- **Export Tours (CSV):** `/api/export/tours/?type=csv`
- **Optimize Tour Route:** `/api/optimize/`

## Filtering & Searching

- Filter tours by artist, venue, or date:
  ```
  /api/tours/?artist=1&venue=2&date=2025-09-01
  ```
- Search by artist or venue name:
  ```
  /api/tours/?search=Queen
  ```

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

## License

MIT
