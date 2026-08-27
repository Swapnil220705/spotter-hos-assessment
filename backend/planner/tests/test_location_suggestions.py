"""
Tests for location autocomplete/suggestion feature.

Covers:
- Query too short (< 3 chars)
- Successful Nominatim response (mocked)
- Empty Nominatim response (mocked)
- Nominatim timeout / network failure (mocked)
- Malformed Nominatim response (mocked)
- Normalized suggestion fields
- In-process cache hit (same query served without a second HTTP call)
- API endpoint returns correct JSON structure
- API endpoint rejects missing/too-short query
- Rate limiting: two different queries are separated by ≥ 1 second
- Rate limiting: concurrent identical queries produce only one Nominatim call
- Rate limiting: cached query produces no additional Nominatim call
"""

import threading
import time
import pytest
from unittest.mock import patch, MagicMock, call
from rest_framework.test import APIClient

import planner.services.geocoding as geocoding_module
from planner.services.geocoding import suggest_locations, _cached_suggest, _reset_rate_limiter


# ---------------------------------------------------------------------------
# Shared test helpers
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


@pytest.fixture(autouse=True)
def reset_limiter():
    """
    Reset cache and rate-limiter state before every test so tests are fully
    isolated from each other. autouse=True means this runs for every test
    in this module without needing to request it explicitly.
    """
    _reset_rate_limiter()
    yield
    _reset_rate_limiter()


# ---------------------------------------------------------------------------
# Existing unit tests (unchanged behaviour, updated cache-clear call)
# ---------------------------------------------------------------------------

# Test 1 — query shorter than minimum length returns empty list without HTTP call
def test_suggest_too_short_returns_empty():
    with patch("planner.services.geocoding.requests.get") as mock_get:
        result = suggest_locations("Ch")
        assert result == []
        mock_get.assert_not_called()


# Test 2 — query of exactly 3 chars is accepted, Nominatim is called
def test_suggest_minimum_length_accepted():
    with patch("planner.services.geocoding.requests.get") as mock_get:
        mock_get.return_value = _make_mock_response()
        result = suggest_locations("Chi")
        assert isinstance(result, list)
        mock_get.assert_called_once()


# Test 3 — successful response is normalized correctly
def test_suggest_successful_response_normalized():
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
    with patch("planner.services.geocoding.requests.get") as mock_get:
        mock_get.return_value = _make_mock_response(json_data=[])
        result = suggest_locations("Zzzzz")
        assert result == []


# Test 5 — Nominatim timeout returns empty list (no exception raised to caller)
def test_suggest_nominatim_timeout():
    import requests as req_lib
    with patch("planner.services.geocoding.requests.get", side_effect=req_lib.Timeout):
        result = suggest_locations("Chicago")
        assert result == []


# Test 6 — Nominatim generic network failure returns empty list
def test_suggest_nominatim_network_failure():
    import requests as req_lib
    with patch(
        "planner.services.geocoding.requests.get",
        side_effect=req_lib.RequestException("connection refused"),
    ):
        result = suggest_locations("Dallas")
        assert result == []


# Test 7 — malformed (non-list) Nominatim response returns empty list
def test_suggest_malformed_response():
    with patch("planner.services.geocoding.requests.get") as mock_get:
        mock_get.return_value = _make_mock_response(json_data={"error": "bad"})
        result = suggest_locations("Atlanta")
        assert result == []


# Test 8 — HTTP non-200 response returns empty list
def test_suggest_non_200_response():
    with patch("planner.services.geocoding.requests.get") as mock_get:
        mock_get.return_value = _make_mock_response(status_code=503, json_data=[])
        result = suggest_locations("Houston")
        assert result == []


# Test 9 — identical query served from cache (Nominatim called only once)
def test_suggest_cache_hit_same_query():
    with patch("planner.services.geocoding.requests.get") as mock_get:
        mock_get.return_value = _make_mock_response()
        suggest_locations("Dallas tx")
        suggest_locations("Dallas tx")  # same query → cache hit
        # Nominatim should only have been called once
        assert mock_get.call_count == 1


# ---------------------------------------------------------------------------
# Existing API endpoint tests (unchanged)
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


# ---------------------------------------------------------------------------
# Rate-limiter tests (new)
# ---------------------------------------------------------------------------

def test_rate_limit_different_queries_enforces_sleep():
    """
    Two different queries that arrive immediately after each other must produce
    a sleep so that the second Nominatim request is delayed by ≥ 1 second.

    Strategy: mock time.monotonic to simulate the second call arriving only
    0.3 seconds after the first, then verify time.sleep is called with a
    value close to 0.7 seconds (the remaining gap to reach 1.0 s).
    """
    # Simulate: first call completes at monotonic t=100.0
    #           second call enters limiter at t=100.3  (only 0.3 s gap → sleep needed)
    monotonic_sequence = [
        # First call — _fetch_from_nominatim executes, then _last_nominatim_time = monotonic()
        100.0,   # elapsed check: 100.0 - 0.0 = big → no sleep
        100.05,  # timestamp recorded after first request
        # Second call — different query arrives 0.3 s later
        100.35,  # elapsed check: 100.35 - 100.05 = 0.3 → sleep needed
        100.36,  # timestamp recorded after second request
    ]
    monotonic_iter = iter(monotonic_sequence)

    with patch("planner.services.geocoding.time.monotonic", side_effect=lambda: next(monotonic_iter)):
        with patch("planner.services.geocoding.time.sleep") as mock_sleep:
            with patch("planner.services.geocoding.requests.get") as mock_get:
                mock_get.return_value = _make_mock_response()
                suggest_locations("chicago")
                suggest_locations("dallas")  # different query — must enforce gap

    # sleep should have been called once for the second query
    assert mock_sleep.call_count == 1
    sleep_duration = mock_sleep.call_args[0][0]
    # Expected: 1.0 - 0.3 = 0.7 s (allow small float tolerance)
    assert abs(sleep_duration - 0.7) < 0.01, (
        f"Expected sleep ~0.7s but got {sleep_duration:.4f}s"
    )
    # Both queries must have triggered Nominatim
    assert mock_get.call_count == 2


def test_rate_limit_no_sleep_when_gap_already_sufficient():
    """
    If the gap since the last Nominatim request is already ≥ 1 second,
    no sleep should occur.
    """
    # Simulate: second call arrives 1.5 s after the first (gap is sufficient)
    monotonic_sequence = [
        100.0,   # elapsed check for first call → no sleep
        100.05,  # timestamp after first request
        101.55,  # elapsed check: 101.55 - 100.05 = 1.5 s → no sleep needed
        101.56,  # timestamp after second request
    ]
    monotonic_iter = iter(monotonic_sequence)

    with patch("planner.services.geocoding.time.monotonic", side_effect=lambda: next(monotonic_iter)):
        with patch("planner.services.geocoding.time.sleep") as mock_sleep:
            with patch("planner.services.geocoding.requests.get") as mock_get:
                mock_get.return_value = _make_mock_response()
                suggest_locations("chicago")
                suggest_locations("dallas")

    mock_sleep.assert_not_called()
    assert mock_get.call_count == 2


def test_rate_limit_concurrent_identical_queries_single_nominatim_call():
    """
    Two threads issuing the same uncached query concurrently must result in
    exactly one outgoing Nominatim request. The second thread gets its answer
    from the cache populated by the first thread (double-checked locking).
    """
    results = []
    call_count_holder = [0]

    original_fetch = geocoding_module._fetch_from_nominatim

    def slow_fetch(query_lower):
        call_count_holder[0] += 1
        time.sleep(0.05)  # simulate short network latency
        return original_fetch.__wrapped__(query_lower) if hasattr(original_fetch, "__wrapped__") else [
            {"display_name": "Chicago, Illinois", "short_name": "Chicago", "lat": 41.8781, "lng": -87.6298}
        ]

    with patch("planner.services.geocoding.requests.get") as mock_get:
        mock_get.return_value = _make_mock_response()

        def worker():
            results.append(suggest_locations("chicago"))

        t1 = threading.Thread(target=worker)
        t2 = threading.Thread(target=worker)
        t1.start()
        t2.start()
        t1.join()
        t2.join()

    # Both threads should have gotten results
    assert len(results) == 2
    assert all(isinstance(r, list) for r in results)
    # Nominatim should only have been called once (second thread hit cache)
    assert mock_get.call_count == 1


def test_rate_limit_cached_query_no_additional_nominatim_call():
    """
    A query that is already in the cache must be served without acquiring
    the lock or making any Nominatim request.
    """
    with patch("planner.services.geocoding.requests.get") as mock_get:
        mock_get.return_value = _make_mock_response()
        # First call — populates cache
        r1 = suggest_locations("chicago")
        assert mock_get.call_count == 1

        # Second and third calls — served from cache, zero additional HTTP calls
        r2 = suggest_locations("chicago")
        r3 = suggest_locations("chicago")
        assert mock_get.call_count == 1  # still 1
        assert r1 == r2 == r3


def test_rate_limit_reset_clears_cache_and_timestamp():
    """
    _reset_rate_limiter() must clear the cache so that the next call for
    a previously cached query goes back to Nominatim.
    """
    with patch("planner.services.geocoding.requests.get") as mock_get:
        mock_get.return_value = _make_mock_response()
        suggest_locations("chicago")
        assert mock_get.call_count == 1

    # Reset as done between tests
    _reset_rate_limiter()

    with patch("planner.services.geocoding.requests.get") as mock_get2:
        mock_get2.return_value = _make_mock_response()
        suggest_locations("chicago")
        # Cache was cleared — Nominatim must be called again
        assert mock_get2.call_count == 1
