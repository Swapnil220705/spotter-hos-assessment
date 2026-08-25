# Spotter AI HOS & Route Planner

A full-stack Hours of Service (HOS) and route planning application built for the Spotter AI Full Stack Developer assessment.

The application plans truck routes, schedules driver duty statuses according to the configured FMCSA property-carrier HOS rules, displays planned stops on an interactive map, and generates multi-day Driver's Daily Log (ELD) sheets.

## Tech Stack

### Backend
- Python
- Django
- Django REST Framework
- Pytest
- OpenStreetMap Nominatim for geocoding
- OSRM for road routing

### Frontend
- React
- Vite
- Leaflet
- React Leaflet
- Lucide React
- SVG-based ELD log renderer

## Features

- Current location, pickup location, and dropoff location inputs
- Current 70-hour / 8-day cycle usage input
- Route planning using OSRM
- OpenStreetMap interactive route map
- Planned pickup, dropoff, fuel, break, and rest waypoints
- HOS-aware trip scheduling
- Multi-day trip planning
- FMCSA-style 24-hour Driver's Daily Log / ELD sheets
- Duty-status graph for:
  - OFF DUTY
  - SLEEPER BERTH
  - DRIVING
  - ON DUTY
- Daily status totals
- Location and activity remarks
- Multi-day ELD navigation
- Printable ELD log sheets

## HOS Rules Implemented

The scheduler is designed around the property-carrying driver assumptions used for this assessment:

- 11-hour maximum driving limit
- 14-hour duty window
- 30-minute break after 8 cumulative hours of driving
- 10 consecutive hours of off-duty rest
- 70-hour / 8-day rolling cycle
- 34-hour restart
- Fueling stop at least once every 1,000 miles
- 0.5-hour fueling activity
- 1-hour pickup activity
- 1-hour dropoff activity
- Four duty statuses:
  - OFF
  - SB
  - D
  - ON

The scheduler independently tracks driving time, the 14-hour duty window, cycle usage, and cumulative driving since the last qualifying break.

## Project Structure

```text
spotter-hos-assessment/
├── backend/
│   ├── manage.py
│   ├── planner/
│   │   ├── services/
│   │   │   ├── geocoding.py
│   │   │   ├── hos_engine.py
│   │   │   ├── log_partitioner.py
│   │   │   └── routing.py
│   │   ├── tests/
│   │   │   └── test_hos_engine.py
│   │   ├── views.py
│   │   └── urls.py
│   ├── spotter_hos/
│   │   ├── settings.py
│   │   └── urls.py
│   ├── requirements.txt
│   └── pytest.ini
│
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── EldLogViewer.jsx
│   │   │   ├── RouteMap.jsx
│   │   │   ├── TripForm.jsx
│   │   │   └── TripSummary.jsx
│   │   ├── services/
│   │   │   └── api.js
│   │   ├── App.jsx
│   │   └── App.css
│   ├── package.json
│   └── vite.config.js
│
├── AGENTS.md
├── README.md
└── .gitignore