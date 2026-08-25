import pytest
from datetime import datetime
from rest_framework.test import APIClient
from planner.services.hos_engine import HOSScheduler, DutyStatus
from planner.services.log_partitioner import partition_events_by_day

@pytest.fixture
def sample_locations():
    return {
        "chicago": {"name": "Chicago, IL", "lat": 41.8781, "lng": -87.6298},
        "indianapolis": {"name": "Indianapolis, IN", "lat": 39.7684, "lng": -86.1581},
        "dallas": {"name": "Dallas, TX", "lat": 32.7767, "lng": -96.7970},
        "los_angeles": {"name": "Los Angeles, CA", "lat": 34.0522, "lng": -118.2437}
    }

def test_short_trip_no_breaks_needed(sample_locations):
    """Short trip (~180 miles, ~3.3h driving): should complete with 1h pickup + drive + 1h dropoff."""
    scheduler = HOSScheduler(
        current_location=sample_locations["chicago"],
        pickup_location=sample_locations["chicago"],
        dropoff_location=sample_locations["indianapolis"],
        current_cycle_used=10.0,
        start_datetime=datetime(2026, 8, 25, 8, 0)
    )
    seg1 = {"distance_miles": 0.0, "duration_hours": 0.0}
    seg2 = {"distance_miles": 180.0, "duration_hours": 3.3}

    events = scheduler.generate_schedule(seg1, seg2)
    
    on_duty_events = [ev for ev in events if ev.status == DutyStatus.ON]
    assert len(on_duty_events) >= 2
    assert any("Pickup" in ev.description for ev in on_duty_events)
    assert any("Dropoff" in ev.description for ev in on_duty_events)

    daily_logs = partition_events_by_day(events)
    assert len(daily_logs) >= 1
    for log in daily_logs:
        total = log["summary"]["off_duty"] + log["summary"]["sleeper_berth"] + log["summary"]["driving"] + log["summary"]["on_duty"]
        assert abs(total - 24.0) < 0.05

def test_30m_break_requirement(sample_locations):
    """500-mile trip (~9.1h driving): must insert a 30-minute break after 8 cumulative drive hours."""
    scheduler = HOSScheduler(
        current_location=sample_locations["chicago"],
        pickup_location=sample_locations["chicago"],
        dropoff_location=sample_locations["dallas"],
        current_cycle_used=0.0,
        start_datetime=datetime(2026, 8, 25, 8, 0)
    )
    seg1 = {"distance_miles": 0.0, "duration_hours": 0.0}
    seg2 = {"distance_miles": 500.0, "duration_hours": 9.1}

    events = scheduler.generate_schedule(seg1, seg2)
    break_events = [ev for ev in events if "30-Minute Rest Break" in ev.description]
    assert len(break_events) >= 1

def test_11h_driving_limit_triggers_10h_rest(sample_locations):
    """750-mile trip (~13.6h driving): must insert a 10-hour rest after reaching 11 driving hours."""
    scheduler = HOSScheduler(
        current_location=sample_locations["chicago"],
        pickup_location=sample_locations["chicago"],
        dropoff_location=sample_locations["dallas"],
        current_cycle_used=0.0,
        start_datetime=datetime(2026, 8, 25, 8, 0)
    )
    seg1 = {"distance_miles": 0.0, "duration_hours": 0.0}
    seg2 = {"distance_miles": 750.0, "duration_hours": 13.6}

    events = scheduler.generate_schedule(seg1, seg2)
    rest_events = [ev for ev in events if "10-Hour Mandatory Rest" in ev.description]
    assert len(rest_events) >= 1

def test_1000m_fuel_stop_requirement(sample_locations):
    """1,200-mile trip: must insert a fuel stop before or at 1,000 miles."""
    scheduler = HOSScheduler(
        current_location=sample_locations["chicago"],
        pickup_location=sample_locations["chicago"],
        dropoff_location=sample_locations["los_angeles"],
        current_cycle_used=0.0,
        start_datetime=datetime(2026, 8, 25, 8, 0)
    )
    seg1 = {"distance_miles": 0.0, "duration_hours": 0.0}
    seg2 = {"distance_miles": 1200.0, "duration_hours": 21.8}

    events = scheduler.generate_schedule(seg1, seg2)
    fuel_events = [ev for ev in events if "Fueling Stop" in ev.description]
    assert len(fuel_events) >= 1

def test_70h_cycle_restart(sample_locations):
    """Starting trip with 68 hours cycle used: must trigger 34h restart when reaching 70 hours."""
    scheduler = HOSScheduler(
        current_location=sample_locations["chicago"],
        pickup_location=sample_locations["chicago"],
        dropoff_location=sample_locations["dallas"],
        current_cycle_used=68.0,
        start_datetime=datetime(2026, 8, 25, 8, 0)
    )
    seg1 = {"distance_miles": 0.0, "duration_hours": 0.0}
    seg2 = {"distance_miles": 300.0, "duration_hours": 5.4}

    events = scheduler.generate_schedule(seg1, seg2)
    restart_events = [ev for ev in events if "34-Hour" in ev.description]
    assert len(restart_events) >= 1

def test_daily_log_totals_always_sum_to_24h(sample_locations):
    """Verifies that every generated daily log sheet sums to exactly 24.0 hours."""
    scheduler = HOSScheduler(
        current_location=sample_locations["chicago"],
        pickup_location=sample_locations["indianapolis"],
        dropoff_location=sample_locations["los_angeles"],
        current_cycle_used=15.0,
        start_datetime=datetime(2026, 8, 25, 8, 0)
    )
    seg1 = {"distance_miles": 180.0, "duration_hours": 3.3}
    seg2 = {"distance_miles": 2000.0, "duration_hours": 36.3}

    events = scheduler.generate_schedule(seg1, seg2)
    daily_logs = partition_events_by_day(events)

    assert len(daily_logs) > 1
    for log in daily_logs:
        summary = log["summary"]
        total = summary["off_duty"] + summary["sleeper_berth"] + summary["driving"] + summary["on_duty"]
        assert round(total, 1) == 24.0

@pytest.mark.django_db
def test_plan_trip_api_endpoint():
    """Integration test for POST /api/plan-trip/ endpoint."""
    client = APIClient()
    response = client.post("/api/plan-trip/", {
        "current_location": "Chicago, IL",
        "pickup_location": "Indianapolis, IN",
        "dropoff_location": "Dallas, TX",
        "current_cycle_used": 15.0
    }, format="json")

    assert response.status_code == 200
    res_data = response.json()
    assert res_data["status"] == "success"
    assert "summary" in res_data
    assert "route" in res_data
    assert "daily_logs" in res_data
    assert len(res_data["daily_logs"]) >= 1
    assert len(res_data["route"]["waypoints"]) >= 2
