"""
Tests for location autocomplete/suggestion feature.

Covers:
- Query too short (< 3 chars)
- Successful Nominatim response (mocked)
- Empty Nominatim response (mocked)
- Nominatim timeout / network failure (mocked)
- Malformed Nominatim response (mocked)
- Normalized suggestion fields
- In-process LRU cache hit (same query served without a second HTTP call)
- API endpoint returns correct JSON structure
- API endpoint rejects missing/too-short query
"""

import pytest
from unittest.mock import patch, MagicMock
from rest_framework.test import APIClient

from planner.services.geocoding import suggest_locations, _cached_suggest


# ---------------------------------------------------------------------------
# Unit tests for suggest_locations() / _cached_suggest()
# ---------------------------------------------------------------------------

NOMINATIM_SAMPLE = [
    {
        "place_id": 1,
        "display_name": "Chicago, Cook County, Illinois, United States",
        "lat": "41.8781",
        "lon": "-87.6298",
        "address": {
            "city": "Chicago",
            "county": "Cook County",
            "state": "Illinois",
            "country": "United States",
        },
    },
    {
        "place_id": 2,
        "display_name": "Chicago Heights, Cook County, Illinois, United States",
        "lat": "41.5061",
        "lon": "-87.6353",
        "address": {
            "city": "Chicago Heights",
            "state": "Illinois",
            "country": "United States",
        },
    },
]


def _make_mock_response(status_code=200, json_data=None):
    mock_resp = MagicMock()
    mock_resp.status_code = status_code
    mock_resp.json.return_value = json_data if json_data is not None else NOMINATIM_SAMPLE
    return mock_resp


# Test 1 — query shorter than minimum length returns empty list without HTTP call
def test_suggest_too_short_returns_empty():
    with patch("planner.services.geocoding.requests.get") as mock_get:
        result = suggest_locations("Ch")
        assert result == []
        mock_get.assert_not_called()


# Test 2 — query of exactly 3 chars is accepted, Nominatim is called
def test_suggest_minimum_length_accepted():
    _cached_suggest.cache_clear()
    with patch("planner.services.geocoding.requests.get") as mock_get:
        mock_get.return_value = _make_mock_response()
        result = suggest_locations("Chi")
        assert isinstance(result, list)
        mock_get.assert_called_once()


# Test 3 — successful response is normalized correctly
def test_suggest_successful_response_normalized():
    _cached_suggest.cache_clear()
    with patch("planner.services.geocoding.requests.get") as mock_get:
        mock_get.return_value = _make_mock_response(json_data=NOMINATIM_SAMPLE)
        result = suggest_locations("Chicago")
        assert len(result) == 2
        first = result[0]
        assert "display_name" in first
        assert "short_name" in first
        assert "lat" in first
        assert "lng" in first
        assert isinstance(first["lat"], float)
        assert isinstance(first["lng"], float)
        assert first["display_name"] == "Chicago, Cook County, Illinois, United States"
        assert "Chicago" in first["short_name"]


# Test 4 — empty Nominatim response returns empty list
def test_suggest_empty_nominatim_response():
    _cached_suggest.cache_clear()
    with patch("planner.services.geocoding.requests.get") as mock_get:
        mock_get.return_value = _make_mock_response(json_data=[])
        result = suggest_locations("Zzzzz")
        assert result == []


# Test 5 — Nominatim timeout returns empty list (no exception raised to caller)
def test_suggest_nominatim_timeout():
    _cached_suggest.cache_clear()
    import requests as req_lib
    with patch("planner.services.geocoding.requests.get", side_effect=req_lib.Timeout):
        result = suggest_locations("Chicago")
        assert result == []


# Test 6 — Nominatim generic network failure returns empty list
def test_suggest_nominatim_network_failure():
    _cached_suggest.cache_clear()
    import requests as req_lib
    with patch(
        "planner.services.geocoding.requests.get",
        side_effect=req_lib.RequestException("connection refused"),
    ):
        result = suggest_locations("Dallas")
        assert result == []


# Test 7 — malformed (non-list) Nominatim response returns empty list
def test_suggest_malformed_response():
    _cached_suggest.cache_clear()
    with patch("planner.services.geocoding.requests.get") as mock_get:
        mock_get.return_value = _make_mock_response(json_data={"error": "bad"})
        result = suggest_locations("Atlanta")
        assert result == []


# Test 8 — HTTP non-200 response returns empty list
def test_suggest_non_200_response():
    _cached_suggest.cache_clear()
    with patch("planner.services.geocoding.requests.get") as mock_get:
        mock_get.return_value = _make_mock_response(status_code=503, json_data=[])
        result = suggest_locations("Houston")
        assert result == []


# Test 9 — identical query is served from LRU cache (Nominatim called only once)
def test_suggest_lru_cache_hit():
    _cached_suggest.cache_clear()
    with patch("planner.services.geocoding.requests.get") as mock_get:
        mock_get.return_value = _make_mock_response()
        suggest_locations("Dallas tx")
        suggest_locations("Dallas tx")  # same query → cache hit
        # Nominatim should only have been called once
        assert mock_get.call_count == 1


# ---------------------------------------------------------------------------
# API endpoint tests
# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_location_suggestions_endpoint_missing_query():
    """GET /api/location-suggestions/ with no q param returns 400."""
    client = APIClient()
    response = client.get("/api/location-suggestions/")
    assert response.status_code == 400
    data = response.json()
    assert "suggestions" in data


@pytest.mark.django_db
def test_location_suggestions_endpoint_too_short():
    """GET /api/location-suggestions/?q=Ch returns 400."""
    client = APIClient()
    response = client.get("/api/location-suggestions/?q=Ch")
    assert response.status_code == 400


@pytest.mark.django_db
def test_location_suggestions_endpoint_success():
    """GET /api/location-suggestions/?q=Chicago returns 200 with suggestions list."""
    _cached_suggest.cache_clear()
    client = APIClient()
    with patch("planner.services.geocoding.requests.get") as mock_get:
        mock_get.return_value = _make_mock_response()
        response = client.get("/api/location-suggestions/?q=Chicago")
    assert response.status_code == 200
    data = response.json()
    assert "suggestions" in data
    assert isinstance(data["suggestions"], list)


@pytest.mark.django_db
def test_location_suggestions_endpoint_nominatim_failure_still_200():
    """Nominatim failure should return 200 with empty suggestions, not 500."""
    _cached_suggest.cache_clear()
    client = APIClient()
    import requests as req_lib
    with patch(
        "planner.services.geocoding.requests.get",
        side_effect=req_lib.RequestException,
    ):
        response = client.get("/api/location-suggestions/?q=Dallas")
    assert response.status_code == 200
    data = response.json()
    assert data["suggestions"] == []
