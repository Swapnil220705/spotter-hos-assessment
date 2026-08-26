import pytest
import requests
from unittest.mock import patch, MagicMock
from rest_framework.test import APIClient

from planner.services.routing import get_route_segment, haversine_distance_miles
from planner.services.geocoding import geocode_location, FALLBACK_LOCATIONS


# ============================================================================
# 1. OSRM ROUTING SERVICE TESTS
# ============================================================================

def test_osrm_routing_success():
    """1. Valid OSRM response uses OSRM distance, duration (in hours), and converts [lng, lat] to [lat, lng]."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "routes": [
            {
                "distance": 160934.4,  # 100 miles in meters
                "duration": 7200,       # 2 hours (7200 seconds)
                "geometry": {
                    "coordinates": [
                        [-87.6298, 41.8781],  # [lng, lat] Chicago
                        [-86.1581, 39.7684]   # [lng, lat] Indy
                    ]
                }
            }
        ]
    }

    origin = {"name": "Chicago, IL", "lat": 41.8781, "lng": -87.6298}
    dest = {"name": "Indianapolis, IN", "lat": 39.7684, "lng": -86.1581}

    with patch("requests.get", return_value=mock_response):
        result = get_route_segment(origin, dest)

    assert result["distance_miles"] == 100.0
    assert result["duration_hours"] == 2.0  # Must be 7200/3600, NOT 100/55 = 1.82
    assert result["coordinates"][0] == [41.8781, -87.6298]  # Flipped to [lat, lng]
    assert result["coordinates"][1] == [39.7684, -86.1581]


def test_osrm_routing_timeout_fallback():
    """2. OSRM timeout raises RequestException and falls back to Haversine 55mph route calculation."""
    origin = {"name": "Chicago, IL", "lat": 41.8781, "lng": -87.6298}
    dest = {"name": "Indianapolis, IN", "lat": 39.7684, "lng": -86.1581}

    with patch("requests.get", side_effect=requests.exceptions.Timeout("Connection timed out")):
        result = get_route_segment(origin, dest)

    expected_direct = haversine_distance_miles(41.8781, -87.6298, 39.7684, -86.1581)
    expected_miles = round(expected_direct * 1.25, 1)

    assert result["distance_miles"] == expected_miles
    assert result["duration_hours"] == round(expected_miles / 55.0, 2)
    assert len(result["coordinates"]) > 0


def test_osrm_routing_http_500_fallback():
    """3. OSRM non-200 HTTP response falls back gracefully to Haversine calculation."""
    mock_response = MagicMock()
    mock_response.status_code = 500

    origin = {"name": "Chicago, IL", "lat": 41.8781, "lng": -87.6298}
    dest = {"name": "Indianapolis, IN", "lat": 39.7684, "lng": -86.1581}

    with patch("requests.get", return_value=mock_response):
        result = get_route_segment(origin, dest)

    assert result["distance_miles"] > 0
    assert result["duration_hours"] > 0
    assert len(result["coordinates"]) > 0


def test_osrm_routing_empty_routes_fallback():
    """4. OSRM response with empty routes array falls back to Haversine calculation."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"routes": []}

    origin = {"name": "Chicago, IL", "lat": 41.8781, "lng": -87.6298}
    dest = {"name": "Indianapolis, IN", "lat": 39.7684, "lng": -86.1581}

    with patch("requests.get", return_value=mock_response):
        result = get_route_segment(origin, dest)

    assert result["distance_miles"] > 0
    assert result["duration_hours"] > 0


def test_osrm_routing_missing_geometry_fallback():
    """5. OSRM route missing geometry polyline falls back to interpolated coordinate points."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "routes": [
            {
                "distance": 160934.4,
                "duration": 7200
                # No geometry provided
            }
        ]
    }

    origin = {"name": "Chicago, IL", "lat": 41.8781, "lng": -87.6298}
    dest = {"name": "Indianapolis, IN", "lat": 39.7684, "lng": -86.1581}

    with patch("requests.get", return_value=mock_response):
        result = get_route_segment(origin, dest)

    assert result["distance_miles"] == 100.0
    assert result["duration_hours"] == 2.0
    assert len(result["coordinates"]) == 21  # 20 interpolated segments = 21 points


# ============================================================================
# 2. GEOCODING SERVICE TESTS
# ============================================================================

def test_geocoding_success():
    """6. Successful Nominatim response returns parsed display name, lat, and lng."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = [
        {
            "display_name": "Chicago, Cook County, Illinois, United States",
            "lat": "41.8781",
            "lon": "-87.6298"
        }
    ]

    with patch("requests.get", return_value=mock_response):
        result = geocode_location("Chicago, IL")

    assert result["name"] == "Chicago, Cook County, Illinois, United States"
    assert result["lat"] == 41.8781
    assert result["lng"] == -87.6298


def test_geocoding_network_failure_known_location_fallback():
    """7. Network failure for known location falls back to curated FALLBACK_LOCATIONS map."""
    with patch("requests.get", side_effect=requests.exceptions.ConnectionError("DNS resolution failed")):
        result = geocode_location("Chicago, IL")

    assert result["lat"] == FALLBACK_LOCATIONS["chicago, il"]["lat"]
    assert result["lng"] == FALLBACK_LOCATIONS["chicago, il"]["lng"]


def test_geocoding_network_failure_unknown_location_fallback():
    """8. Network failure for unknown location query falls back to US geographic center."""
    with patch("requests.get", side_effect=requests.exceptions.Timeout("Geocoding service timeout")):
        result = geocode_location("Random Custom Warehouse 99823")

    assert result["lat"] == 39.8283
    assert result["lng"] == -98.5795
    assert result["name"] == "Random Custom Warehouse 99823"


def test_geocoding_empty_api_result_fallback():
    """9. Empty JSON result array from Nominatim falls back to internal fallback lookup."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = []

    with patch("requests.get", return_value=mock_response):
        result = geocode_location("Dallas, TX")

    assert result["lat"] == FALLBACK_LOCATIONS["dallas, tx"]["lat"]
    assert result["lng"] == FALLBACK_LOCATIONS["dallas, tx"]["lng"]


# ============================================================================
# 3. API-LEVEL RESILIENCE INTEGRATION TESTS
# ============================================================================

@pytest.mark.django_db
def test_api_resilience_when_osrm_offline():
    """10. API POST /api/plan-trip/ succeeds with 200 and valid route when OSRM routing is offline."""
    client = APIClient()

    with patch("requests.get", side_effect=requests.exceptions.ConnectionError("OSRM server down")):
        response = client.post(
            "/api/plan-trip/",
            {
                "current_location": "Chicago, IL",
                "pickup_location": "Indianapolis, IN",
                "dropoff_location": "Dallas, TX",
                "current_cycle_used": 15.0
            },
            format="json"
        )

    assert response.status_code == 200
    res_data = response.json()
    assert res_data["status"] == "success"
    assert res_data["summary"]["total_distance_miles"] > 0
    assert len(res_data["daily_logs"]) >= 1


@pytest.mark.django_db
def test_api_resilience_when_geocoding_offline():
    """11. API POST /api/plan-trip/ succeeds with 200 when Nominatim geocoding is offline."""
    client = APIClient()

    with patch("requests.get", side_effect=requests.exceptions.Timeout("Nominatim timeout")):
        response = client.post(
            "/api/plan-trip/",
            {
                "current_location": "Chicago, IL",
                "pickup_location": "Indianapolis, IN",
                "dropoff_location": "Dallas, TX",
                "current_cycle_used": 15.0
            },
            format="json"
        )

    assert response.status_code == 200
    res_data = response.json()
    assert res_data["status"] == "success"
    assert len(res_data["route"]["waypoints"]) >= 3
