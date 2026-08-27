# HOS & Route Planner

Property-carrier Hours of Service scheduling and ELD log generation application built as a Full Stack Developer assessment for Spotter AI.

The application accepts a current location, pickup location, dropoff location, and current cycle hours used, then produces a planned truck route, HOS-compliant trip schedule, interactive route map, and filled-out FMCSA-style Driver's Daily Log (ELD) sheets — including separate sheets for each calendar day when the trip spans multiple days.

---

## Live Deployment

| | URL |
|---|---|
| **Live Demo (Vercel)** | https://spotter-hos-assessment-theta.vercel.app/ |
| **Backend API (Render)** | https://spotter-hos-backend-86s1.onrender.com |
| **Health Endpoint** | https://spotter-hos-backend-86s1.onrender.com/api/health/ |

> **Note:** The backend runs on Render's free tier. The first request after a period of inactivity may take 30–60 seconds while the service wakes up. The loading overlay in the UI will remain visible during this time.

---

## Features

- **Route Planning** — Geocodes addresses using Nominatim (OpenStreetMap) and routes using OSRM with road-distance-based stop positioning
- **Location Autocomplete** — Real-time location search suggestions via backend proxy with debouncing (350ms), LRU caching, and 1 req/sec rate limiting
- **HOS Scheduling Engine** — Chronological event-driven scheduler applying all FMCSA property-carrier rules
- **Interactive Route Map** — OpenStreetMap/Leaflet map with distinct waypoint markers, polyline route, and legend
- **Trip Event Timeline** — Visual event-by-event timeline of the entire scheduled trip
- **Multi-Day ELD Log Sheets** — FMCSA-style 24-hour duty-status graphs, one per calendar day
- **Printable ELD Logs** — Clean print layout via browser print
- **Custom Driver/Carrier Metadata** — Optional Driver Name, Carrier Name, Truck #, Trailer # shown on all ELD sheets
- **Responsive Design** — Works on desktop, tablet, and mobile (375px+)
- **Three Trip Presets** — Short (~180 mi), Medium (~1,120 mi), Long (~2,800 mi)
- **API Input Validation** — Descriptive error messages for missing or invalid inputs
- **API Health Endpoint** — `GET /api/health/` for deployment monitoring

---

## HOS Rules Implemented

Based on the FMCSA *Interstate Truck Driver's Guide to Hours of Service (April 2022)* reference provided with the assessment:

| Rule | Limit |
|------|-------|
| Maximum driving per shift | 11 hours |
| Duty window (from first work) | 14 consecutive hours |
| 30-minute break trigger | After 8 cumulative driving hours |
| Mandatory off-duty rest | 10 consecutive hours |
| Cycle | 70 hours / 8 days (rolling) |
| 34-hour restart | ≥ 34 consecutive off-duty/sleeper hours |
| Fueling interval | At least once every 1,000 miles |
| Fueling duration | 0.5 hours (on-duty non-driving) |
| Pickup duration | 1 hour (on-duty non-driving) |
| Dropoff duration | 1 hour (on-duty non-driving) |

All four FMCSA duty statuses are tracked: **OFF DUTY**, **SLEEPER BERTH**, **DRIVING**, **ON DUTY (Not Driving)**.

---

## Architecture

```
Browser (React/Vite)
    │
    │  POST /api/plan-trip/
    │  GET  /api/health/
    │  GET  /api/location-suggestions/
    ▼
Django REST Framework (Gunicorn + WhiteNoise)
    │
    ├─ Geocoding Service  (Nominatim → rate-limited proxy & fallbacks)
    ├─ Routing Service    (OSRM → 55 mph duration fallback)
    ├─ HOS Engine         (event-driven chronological scheduler)
    └─ Log Partitioner    (splits events into 24-hour calendar days)
```

**Key design principle:** All HOS calculations and ELD event generation happen on the backend. The frontend only handles display, user input, and map rendering.

---

## Tech Stack

### Backend
- Python 3.11 / Django 5+ / Django REST Framework
- Gunicorn (WSGI server)
- WhiteNoise (static file serving)
- OpenStreetMap Nominatim (geocoding & autocomplete proxy)
- OSRM (road routing)
- Pytest / pytest-django (63 tests)

### Frontend
- React 19 / Vite 8
- Leaflet / React Leaflet (interactive map)
- Lucide React (icons)
- SVG-based ELD graph renderer (custom, no charting library)
- Vanilla CSS with CSS custom properties

---

## Local Development Setup

### Prerequisites
- Python 3.11+
- Node.js 18+
- Git

### Backend Setup

```bash
cd backend
python -m venv venv

# Windows
.\venv\Scripts\activate
# macOS/Linux
source venv/bin/activate

pip install -r requirements.txt
python manage.py migrate
python manage.py runserver 8000
```

Backend runs at: `http://localhost:8000`

### Frontend Setup

```bash
cd frontend
npm install
npm run dev
```

Frontend runs at: `http://localhost:5173`

The frontend automatically uses `http://localhost:8000/api` when no `VITE_API_URL` environment variable is set.

---

## API Reference

### `GET /api/health/`

Health check. Returns HTTP 200 when the service is running.

```json
{
  "status": "ok",
  "service": "Spotter HOS Planner API",
  "version": "1.0.0"
}
```

### `GET /api/location-suggestions/?q=<query>`

Proxy endpoint for location autocomplete suggestions. Returns up to 5 US location suggestions for queries of 3+ characters.

```json
{
  "suggestions": [
    {
      "display_name": "Chicago, Cook County, Illinois, United States",
      "short_name": "Chicago, Illinois",
      "lat": 41.8781,
      "lng": -87.6298
    }
  ]
}
```

### `POST /api/plan-trip/`

Plans a trip and returns HOS schedule, route geometry, waypoints, and daily ELD logs.

**Request body:**
```json
{
  "current_location": "Chicago, IL",
  "pickup_location": "Indianapolis, IN",
  "dropoff_location": "Dallas, TX",
  "current_cycle_used": 15
}
```

**Response structure:**
```json
{
  "status": "ok",
  "summary": {
    "total_distance_miles": 1080.3,
    "total_driving_hours": 19.45,
    "total_onduty_hours": 2.5,
    "total_rest_hours": 10.0,
    "total_trip_hours": 31.95,
    "total_days": 2
  },
  "route": {
    "geometry": [[lat, lon], ...],
    "total_distance_miles": 1080.3,
    "total_duration_hours": 19.64
  },
  "waypoints": [
    {
      "type": "origin|pickup|dropoff|fuel|rest|break|restart",
      "name": "...",
      "lat": 41.8827,
      "lon": -87.6233,
      "time": "2026-08-26T08:00:00"
    }
  ],
  "daily_logs": [
    {
      "date": "2026-08-26",
      "events": [
        {
          "status": "OFF|D|ON|SB",
          "start_time": "2026-08-26T00:00:00",
          "end_time": "2026-08-26T08:00:00",
          "location": "...",
          "remark": "..."
        }
      ],
      "totals": {"OFF": 12.0, "D": 11.0, "ON": 1.0, "SB": 0.0},
      "miles_today": 600.4
    }
  ]
}
```

---

## Production Deployment

### Environment Variables

**Backend (Render):**

| Variable | Description |
|----------|-------------|
| `DJANGO_SECRET_KEY` | Cryptographic secret (auto-generated by Render) |
| `DJANGO_DEBUG` | `False` in production |
| `DJANGO_ALLOWED_HOSTS` | Comma-separated allowed host domains |
| `DJANGO_CORS_ALLOWED_ORIGINS` | Comma-separated allowed CORS origins (e.g., Vercel URL) |
| `DJANGO_SETTINGS_MODULE` | `spotter_hos.settings` |

**Frontend (Vercel):**

| Variable | Description |
|----------|-------------|
| `VITE_API_URL` | Backend API base URL, e.g. `https://spotter-hos-backend-86s1.onrender.com/api` |

### Render Deployment

The repository includes `render.yaml` configured for Render's free tier:

```bash
# Build command
cd backend && pip install -r requirements.txt && python manage.py collectstatic --noinput

# Start command
cd backend && gunicorn spotter_hos.wsgi:application --bind 0.0.0.0:$PORT --workers 1 --timeout 120
```

### Vercel Deployment

The repository includes `frontend/vercel.json`. Set Root Directory to `frontend` in the Vercel project settings.

---

## Testing

```bash
cd backend
.\venv\Scripts\python.exe -m pytest -q
```

**63 tests** covering:
- HOS engine: 11h limit, 14h window, 30-minute break, 10h rest, 70h cycle, 34h restart
- Edge cases: zero-distance trips, approaching cycle limit, multiple restarts
- Daily log partitioner: midnight event splitting, multi-day generation, correct hourly totals
- Routing/geocoding resilience: OSRM failures, Nominatim failures, combined fallbacks
- Location autocomplete: debouncing, rate limiting, cache hits, thread safety, endpoint validation
- API validation: missing fields, invalid cycle values, blank locations
- API health endpoint

```bash
cd frontend
npm run lint   # 2 known non-blocking warnings, 0 errors
npm run build  # production build
```

---

## Project Structure

```
spotter-hos-assessment/
├── backend/
│   ├── manage.py
│   ├── requirements.txt
│   ├── pytest.ini
│   ├── planner/
│   │   ├── services/
│   │   │   ├── geocoding.py       # Nominatim geocoding + autocomplete proxy & fallbacks
│   │   │   ├── routing.py         # OSRM routing + fallback
│   │   │   ├── hos_engine.py      # HOS scheduling engine
│   │   │   └── log_partitioner.py # 24-hour ELD day partitioner
│   │   ├── tests/
│   │   │   ├── test_hos_engine.py
│   │   │   ├── test_api_health.py
│   │   │   ├── test_location_suggestions.py
│   │   │   └── test_routing_geocoding.py
│   │   ├── views.py               # API endpoints
│   │   └── urls.py
│   └── spotter_hos/
│       └── settings.py            # Environment-driven config
│
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── TripForm.jsx       # Input form with autocomplete, presets & metadata
│   │   │   ├── RouteMap.jsx       # Leaflet map with custom markers
│   │   │   ├── EventTimeline.jsx  # HOS event timeline
│   │   │   ├── TripSummary.jsx    # Summary metric cards
│   │   │   └── EldLogViewer.jsx   # SVG ELD graph + remarks table
│   │   ├── services/
│   │   │   └── api.js             # fetch wrapper using VITE_API_URL
│   │   ├── App.jsx                # Root component and state
│   │   └── index.css              # Design system and responsive CSS
│   ├── vercel.json
│   └── vite.config.js
│
├── render.yaml                    # Render free-tier Blueprint
├── AGENTS.md                      # Project rules for AI development
└── README.md
```