import pytest
from unittest.mock import patch
from datetime import datetime, timedelta
from rest_framework.test import APIClient
from planner.services.hos_engine import HOSScheduler, DutyStatus, interpolate_polyline_coordinate
from planner.services.log_partitioner import partition_events_by_day


@pytest.fixture
def sample_locations():
    return {
        "chicago": {"name": "Chicago, IL", "lat": 41.8781, "lng": -87.6298},
        "indianapolis": {"name": "Indianapolis, IN", "lat": 39.7684, "lng": -86.1581},
        "dallas": {"name": "Dallas, TX", "lat": 32.7767, "lng": -96.7970},
        "los_angeles": {"name": "Los Angeles, CA", "lat": 34.0522, "lng": -118.2437}
    }


def test_osrm_duration_used(sample_locations):
    """1. OSRM duration is respected when specified in segment route."""
    scheduler = HOSScheduler(
        current_location=sample_locations["chicago"],
        pickup_location=sample_locations["chicago"],
        dropoff_location=sample_locations["indianapolis"],
        current_cycle_used=0.0,
        start_datetime=datetime(2026, 8, 25, 8, 0)
    )

    seg1 = {"distance_miles": 0.0, "duration_hours": 0.0}
    seg2 = {"distance_miles": 180.0, "duration_hours": 4.0}

    events = scheduler.generate_schedule(seg1, seg2)
    drive_events = [ev for ev in events if ev.status == DutyStatus.D]
    total_drive_hours = sum(ev.duration_hours for ev in drive_events)

    assert abs(total_drive_hours - 4.0) < 0.05


def test_short_trip_exact_timeline(sample_locations):
    """2. Short trip exact timeline: Pickup (1h ON) -> Drive -> Dropoff (1h ON)."""
    scheduler = HOSScheduler(
        current_location=sample_locations["chicago"],
        pickup_location=sample_locations["chicago"],
        dropoff_location=sample_locations["indianapolis"],
        current_cycle_used=10.0,
        start_datetime=datetime(2026, 8, 25, 8, 0)
    )

    seg1 = {"distance_miles": 0.0, "duration_hours": 0.0}
    seg2 = {"distance_miles": 180.0, "duration_hours": 3.0}

    events = scheduler.generate_schedule(seg1, seg2)

    assert events[0].status == DutyStatus.ON
    assert events[0].duration_hours == 1.0
    assert "Pickup" in events[0].description
    assert events[0].start_time == datetime(2026, 8, 25, 8, 0)
    assert events[0].end_time == datetime(2026, 8, 25, 9, 0)

    assert events[1].status == DutyStatus.D
    assert abs(events[1].duration_hours - 3.0) < 0.05
    assert events[1].start_time == datetime(2026, 8, 25, 9, 0)

    assert events[2].status == DutyStatus.ON
    assert events[2].duration_hours == 1.0
    assert "Dropoff" in events[2].description


def test_8h_cumulative_drive_break_exact(sample_locations):
    """3. 30-minute break inserted after exact 8.0 cumulative driving hours."""
    scheduler = HOSScheduler(
        current_location=sample_locations["chicago"],
        pickup_location=sample_locations["chicago"],
        dropoff_location=sample_locations["dallas"],
        current_cycle_used=0.0,
        start_datetime=datetime(2026, 8, 25, 8, 0)
    )

    seg1 = {"distance_miles": 0.0, "duration_hours": 0.0}
    seg2 = {"distance_miles": 500.0, "duration_hours": 10.0}

    events = scheduler.generate_schedule(seg1, seg2)

    break_events = [ev for ev in events if "30-Minute Rest Break" in ev.description]

    assert len(break_events) >= 1
    assert break_events[0].start_time == datetime(2026, 8, 25, 17, 0)
    assert break_events[0].duration_hours == 0.5


def test_11h_driving_limit_exact(sample_locations):
    """4. 10-hour rest is inserted exactly after reaching 11.0 cumulative driving hours."""
    scheduler = HOSScheduler(
        current_location=sample_locations["chicago"],
        pickup_location=sample_locations["chicago"],
        dropoff_location=sample_locations["dallas"],
        current_cycle_used=0.0,
        start_datetime=datetime(2026, 8, 25, 8, 0)
    )

    seg1 = {"distance_miles": 0.0, "duration_hours": 0.0}
    seg2 = {"distance_miles": 750.0, "duration_hours": 13.0}

    events = scheduler.generate_schedule(seg1, seg2)

    rest_events = [
        ev for ev in events
        if "10-Hour Mandatory Rest" in ev.description
    ]

    assert len(rest_events) >= 1

    rest_event = rest_events[0]

    # Pickup consumes 1 hour, so driving starts at 09:00.
    # After 8 hours of driving, a 30-minute break is required:
    # 09:00 -> 17:00 driving
    # 17:00 -> 17:30 break
    # 17:30 -> 20:30 driving
    # Therefore the 11-hour driving limit is reached at 20:30.
    assert rest_event.start_time == datetime(2026, 8, 25, 20, 30)
    assert rest_event.duration_hours == 10.0

    # Driving is split by the mandatory 30-minute break, so the
    # driving event immediately before the rest is only the final
    # 3 hours. Verify that cumulative driving before the 10-hour
    # rest is exactly 11 hours.
    rest_index = events.index(rest_event)
    assert rest_index > 0

    driving_before_rest = events[rest_index - 1]
    assert driving_before_rest.status == DutyStatus.D
    assert driving_before_rest.end_time == rest_event.start_time

    driving_before_rest_total = sum(
        ev.duration_hours
        for ev in events[:rest_index]
        if ev.status == DutyStatus.D
    )

    assert abs(driving_before_rest_total - 11.0) < 0.05


def test_14h_duty_window_exact(sample_locations):
    """5. 10-hour rest inserted when 14.0 consecutive duty window hours elapse."""
    scheduler = HOSScheduler(
        current_location=sample_locations["chicago"],
        pickup_location=sample_locations["chicago"],
        dropoff_location=sample_locations["dallas"],
        current_cycle_used=0.0,
        start_datetime=datetime(2026, 8, 25, 8, 0)
    )

    seg1 = {"distance_miles": 0.0, "duration_hours": 0.0}
    seg2 = {"distance_miles": 650.0, "duration_hours": 11.0}

    scheduler._handle_on_duty_task(
        "Pre-Trip Inspection",
        3.0,
        sample_locations["chicago"]
    )

    events = scheduler.generate_schedule(seg1, seg2)

    rest_events = [
        ev for ev in events
        if "10-Hour Mandatory Rest" in ev.description
    ]

    assert len(rest_events) >= 1


def test_11h_drive_limit_allows_on_duty_work(sample_locations):
    """6. 11h driving limit stops driving but allows ON-duty work if within 14h window."""
    scheduler = HOSScheduler(
        current_location=sample_locations["chicago"],
        pickup_location=sample_locations["chicago"],
        dropoff_location=sample_locations["dallas"],
        current_cycle_used=0.0,
        start_datetime=datetime(2026, 8, 25, 8, 0)
    )

    seg1 = {"distance_miles": 0.0, "duration_hours": 0.0}

    # 11 hours of driving reaches the driving limit exactly.
    # Pickup occurs first for 1 hour, so driving runs from 09:00 to 20:00.
    seg2 = {"distance_miles": 605.0, "duration_hours": 11.0}

    events = scheduler.generate_schedule(seg1, seg2)

    dropoff_events = [
        ev for ev in events
        if ev.status == DutyStatus.ON and "Dropoff" in ev.description
    ]

    assert len(dropoff_events) >= 1

    dropoff_event = dropoff_events[-1]

    assert dropoff_event.status == DutyStatus.ON
    assert dropoff_event.duration_hours == 1.0
    assert "Dropoff" in dropoff_event.description

    # The driver must have reached the 11-hour driving limit.
    total_driving_hours = sum(
        ev.duration_hours
        for ev in events
        if ev.status == DutyStatus.D
    )
    assert total_driving_hours >= 11.0


def test_pickup_1h_on_duty_sequence(sample_locations):
    """7. Pickup is exactly 1.0 hour ON duty and occurs after arrival at pickup."""
    scheduler = HOSScheduler(
        current_location=sample_locations["chicago"],
        pickup_location=sample_locations["indianapolis"],
        dropoff_location=sample_locations["dallas"],
        current_cycle_used=0.0,
        start_datetime=datetime(2026, 8, 25, 8, 0)
    )

    seg1 = {"distance_miles": 180.0, "duration_hours": 3.0}
    seg2 = {"distance_miles": 800.0, "duration_hours": 14.0}

    events = scheduler.generate_schedule(seg1, seg2)

    assert events[0].status == DutyStatus.D
    assert events[0].location_name == "En Route (to Indianapolis, IN)"

    assert events[1].status == DutyStatus.ON
    assert events[1].duration_hours == 1.0
    assert events[1].location_name == "Indianapolis, IN"
    assert "Pickup" in events[1].description


def test_dropoff_1h_on_duty_sequence(sample_locations):
    """8. Dropoff is exactly 1.0 hour ON duty and occurs after completing Segment 2."""
    scheduler = HOSScheduler(
        current_location=sample_locations["chicago"],
        pickup_location=sample_locations["chicago"],
        dropoff_location=sample_locations["indianapolis"],
        current_cycle_used=0.0,
        start_datetime=datetime(2026, 8, 25, 8, 0)
    )

    seg1 = {"distance_miles": 0.0, "duration_hours": 0.0}
    seg2 = {"distance_miles": 180.0, "duration_hours": 3.0}

    events = scheduler.generate_schedule(seg1, seg2)

    last_event = events[-1]

    assert last_event.status == DutyStatus.ON
    assert last_event.duration_hours == 1.0
    assert last_event.location_name == "Indianapolis, IN"
    assert "Dropoff" in last_event.description


def test_fuel_stop_near_14h_window_boundary(sample_locations):
    """9. Fuel stop near 14h window boundary inserts a 10h rest BEFORE fueling if 0.5h won't fit."""
    scheduler = HOSScheduler(
        current_location=sample_locations["chicago"],
        pickup_location=sample_locations["chicago"],
        dropoff_location=sample_locations["los_angeles"],
        current_cycle_used=0.0,
        start_datetime=datetime(2026, 8, 25, 8, 0)
    )

    # Manually advance shift elapsed time to 13.8 hours.
    scheduler.shift_start_time = scheduler.current_time - timedelta(hours=13.8)

    scheduler._insert_fuel_stop(
        "Highway Fuel Station",
        36.0,
        -90.0
    )

    events = scheduler.events

    assert events[-2].status == DutyStatus.OFF
    assert "10-Hour Mandatory Rest" in events[-2].description
    assert events[-1].status == DutyStatus.ON
    assert "Fueling Stop" in events[-1].description


def test_fuel_stop_near_70h_cycle_boundary(sample_locations):
    """10. Fuel stop near 70h cycle boundary inserts a 34h restart BEFORE fueling if 0.5h won't fit."""
    scheduler = HOSScheduler(
        current_location=sample_locations["chicago"],
        pickup_location=sample_locations["chicago"],
        dropoff_location=sample_locations["los_angeles"],
        current_cycle_used=69.8,
        start_datetime=datetime(2026, 8, 25, 8, 0)
    )

    scheduler._insert_fuel_stop(
        "Highway Fuel Station",
        36.0,
        -90.0
    )

    events = scheduler.events

    assert events[-2].status == DutyStatus.OFF
    assert "34-Hour" in events[-2].description
    assert events[-1].status == DutyStatus.ON
    assert "Fueling Stop" in events[-1].description
    assert scheduler.cycle_hours_used == 0.5


def test_fuel_stop_satisfies_30m_break_requirement(sample_locations):
    """11. Fuel stop resets cumulative driving since last break."""
    scheduler = HOSScheduler(
        current_location=sample_locations["chicago"],
        pickup_location=sample_locations["chicago"],
        dropoff_location=sample_locations["los_angeles"],
        current_cycle_used=0.0,
        start_datetime=datetime(2026, 8, 25, 8, 0)
    )

    scheduler.drive_since_last_break = 7.5

    scheduler._insert_fuel_stop(
        "Highway Fuel Station",
        36.0,
        -90.0
    )

    assert scheduler.drive_since_last_break == 0.0


def test_1000m_fueling_behavior(sample_locations):
    """12. 1,000-mile fueling milestone triggers, resets mileage, and logs FUEL waypoint."""
    scheduler = HOSScheduler(
        current_location=sample_locations["chicago"],
        pickup_location=sample_locations["chicago"],
        dropoff_location=sample_locations["los_angeles"],
        current_cycle_used=0.0,
        start_datetime=datetime(2026, 8, 25, 8, 0)
    )

    seg1 = {"distance_miles": 0.0, "duration_hours": 0.0}
    seg2 = {"distance_miles": 1200.0, "duration_hours": 20.0}

    events = scheduler.generate_schedule(seg1, seg2)

    fuel_events = [
        ev for ev in events
        if "Fueling Stop" in ev.description
    ]

    fuel_waypoints = [
        wp for wp in scheduler.waypoints
        if wp.waypoint_type == "FUEL"
    ]

    assert len(fuel_events) >= 1
    assert len(fuel_waypoints) >= 1
    assert scheduler.miles_since_last_fuel < 1000.0


def test_cycle_approaching_70h(sample_locations):
    """13. Driving stops before cycle reaches 70.0 hours."""
    scheduler = HOSScheduler(
        current_location=sample_locations["chicago"],
        pickup_location=sample_locations["chicago"],
        dropoff_location=sample_locations["dallas"],
        current_cycle_used=65.0,
        start_datetime=datetime(2026, 8, 25, 8, 0)
    )

    seg1 = {"distance_miles": 0.0, "duration_hours": 0.0}
    seg2 = {"distance_miles": 400.0, "duration_hours": 7.0}

    events = scheduler.generate_schedule(seg1, seg2)

    restart_events = [
        ev for ev in events
        if "34-Hour" in ev.description
    ]

    assert len(restart_events) >= 1


def test_cycle_exhaustion_before_on_duty_task(sample_locations):
    """14. 34h restart is inserted BEFORE an ON-duty task if task would exceed 70.0 hours."""
    scheduler = HOSScheduler(
        current_location=sample_locations["chicago"],
        pickup_location=sample_locations["chicago"],
        dropoff_location=sample_locations["dallas"],
        current_cycle_used=69.5,
        start_datetime=datetime(2026, 8, 25, 8, 0)
    )

    seg1 = {"distance_miles": 0.0, "duration_hours": 0.0}
    seg2 = {"distance_miles": 100.0, "duration_hours": 2.0}

    events = scheduler.generate_schedule(seg1, seg2)

    assert events[0].status == DutyStatus.OFF
    assert events[0].duration_hours == 34.0
    assert "34-Hour" in events[0].description

    assert events[1].status == DutyStatus.ON
    assert "Pickup" in events[1].description


def test_34h_restart_resets_cycle_and_shift(sample_locations):
    """15. 34h restart resets cycle_hours_used to 0.0 and starts a new shift."""
    scheduler = HOSScheduler(
        current_location=sample_locations["chicago"],
        pickup_location=sample_locations["chicago"],
        dropoff_location=sample_locations["dallas"],
        current_cycle_used=70.0,
        start_datetime=datetime(2026, 8, 25, 8, 0)
    )

    seg1 = {"distance_miles": 0.0, "duration_hours": 0.0}
    seg2 = {"distance_miles": 100.0, "duration_hours": 2.0}

    events = scheduler.generate_schedule(seg1, seg2)

    assert events[0].duration_hours == 34.0
    assert scheduler.cycle_hours_used < 70.0


def test_midnight_crossing_events(sample_locations):
    """16. Events crossing 00:00 split cleanly with 00:00 continuation remarks."""
    scheduler = HOSScheduler(
        current_location=sample_locations["chicago"],
        pickup_location=sample_locations["chicago"],
        dropoff_location=sample_locations["dallas"],
        current_cycle_used=0.0,
        start_datetime=datetime(2026, 8, 25, 18, 0)
    )

    seg1 = {"distance_miles": 0.0, "duration_hours": 0.0}
    seg2 = {"distance_miles": 500.0, "duration_hours": 9.0}

    events = scheduler.generate_schedule(seg1, seg2)
    daily_logs = partition_events_by_day(events)

    assert len(daily_logs) >= 2

    day2_remarks = daily_logs[1]["remarks"]
    assert any(
        rmk["time"] == "00:00"
        for rmk in day2_remarks
    )


def test_daily_status_totals_exact_24h(sample_locations):
    """17. Every daily log sheet summary equals exactly 24.0 hours."""
    scheduler = HOSScheduler(
        current_location=sample_locations["chicago"],
        pickup_location=sample_locations["indianapolis"],
        dropoff_location=sample_locations["los_angeles"],
        current_cycle_used=15.0,
        start_datetime=datetime(2026, 8, 25, 8, 0)
    )

    seg1 = {"distance_miles": 180.0, "duration_hours": 3.0}
    seg2 = {"distance_miles": 2000.0, "duration_hours": 36.0}

    events = scheduler.generate_schedule(seg1, seg2)
    daily_logs = partition_events_by_day(events)

    for log in daily_logs:
        summary = log["summary"]

        total = (
            summary["off_duty"]
            + summary["sleeper_berth"]
            + summary["driving"]
            + summary["on_duty"]
        )

        assert round(total, 2) == 24.0


def test_no_unexplained_gaps(sample_locations):
    """18. 00:00 to 24:00 is 100% covered by explicit day events on every log sheet."""
    scheduler = HOSScheduler(
        current_location=sample_locations["chicago"],
        pickup_location=sample_locations["chicago"],
        dropoff_location=sample_locations["indianapolis"],
        current_cycle_used=0.0,
        start_datetime=datetime(2026, 8, 25, 8, 0)
    )

    seg1 = {"distance_miles": 0.0, "duration_hours": 0.0}
    seg2 = {"distance_miles": 180.0, "duration_hours": 3.0}

    events = scheduler.generate_schedule(seg1, seg2)
    daily_logs = partition_events_by_day(events)

    for log in daily_logs:
        day_events = log["events"]

        assert day_events[0]["start_time"] == "00:00"
        assert day_events[-1]["end_time"] == "24:00"

        # Explicitly verify that there are no gaps between adjacent events.
        for i in range(1, len(day_events)):
            assert day_events[i]["start_time"] == day_events[i - 1]["end_time"]

        total_event_hours = sum(
            ev["duration_hours"]
            for ev in day_events
        )

        assert abs(total_event_hours - 24.0) < 0.05


def test_chronological_ordering(sample_locations):
    """19. Events and waypoints follow strict monotonic timestamp ordering."""
    scheduler = HOSScheduler(
        current_location=sample_locations["chicago"],
        pickup_location=sample_locations["indianapolis"],
        dropoff_location=sample_locations["dallas"],
        current_cycle_used=20.0,
        start_datetime=datetime(2026, 8, 25, 8, 0)
    )

    seg1 = {"distance_miles": 180.0, "duration_hours": 3.0}
    seg2 = {"distance_miles": 800.0, "duration_hours": 14.0}

    events = scheduler.generate_schedule(seg1, seg2)

    for i in range(1, len(events)):
        assert events[i].start_time >= events[i - 1].end_time


@pytest.mark.django_db
def test_api_integration_behavior():
    """20. Integration test for POST /api/plan-trip/ endpoint."""
    client = APIClient()

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
    assert "summary" in res_data
    assert "route" in res_data
    assert "daily_logs" in res_data
    assert len(res_data["daily_logs"]) >= 1
    assert len(res_data["route"]["waypoints"]) >= 2


@pytest.mark.django_db
def test_api_validation_missing_required_fields():
    """21. API returns 400 when required location fields are missing."""
    client = APIClient()

    response = client.post(
        "/api/plan-trip/",
        {
            "current_location": "Chicago, IL",
            "pickup_location": "",
            "dropoff_location": "Dallas, TX",
            "current_cycle_used": 10.0
        },
        format="json"
    )

    assert response.status_code == 400
    res_data = response.json()
    assert "error" in res_data
    assert "Missing required fields" in res_data["error"]


@pytest.mark.django_db
def test_api_validation_negative_cycle_used():
    """22. API returns 400 when current_cycle_used is negative."""
    client = APIClient()

    response = client.post(
        "/api/plan-trip/",
        {
            "current_location": "Chicago, IL",
            "pickup_location": "Indianapolis, IN",
            "dropoff_location": "Dallas, TX",
            "current_cycle_used": -5.0
        },
        format="json"
    )

    assert response.status_code == 400
    res_data = response.json()
    assert "error" in res_data
    assert "Invalid current_cycle_used" in res_data["error"]


@pytest.mark.django_db
def test_api_validation_excessive_cycle_used():
    """23. API returns 400 when current_cycle_used exceeds 70 hours."""
    client = APIClient()

    response = client.post(
        "/api/plan-trip/",
        {
            "current_location": "Chicago, IL",
            "pickup_location": "Indianapolis, IN",
            "dropoff_location": "Dallas, TX",
            "current_cycle_used": 75.0
        },
        format="json"
    )

    assert response.status_code == 400
    res_data = response.json()
    assert "error" in res_data
    assert "Invalid current_cycle_used" in res_data["error"]


@pytest.mark.django_db
def test_api_500_internal_error_handling():
    """24. API returns structured JSON 500 response when unexpected server exception occurs."""
    client = APIClient()

    with patch("planner.views.geocode_location", side_effect=Exception("Simulated geocode service crash")):
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

    assert response.status_code == 500
    res_data = response.json()
    assert "error" in res_data
    assert "internal server error" in res_data["error"].lower()


def test_straight_line_geometry_snapping():
    """25. Interpolates halfway along a straight-line polyline geometry."""
    coords = [[40.0, -80.0], [42.0, -80.0]]
    lat, lng = interpolate_polyline_coordinate(coords, 0.5)
    assert abs(lat - 41.0) < 0.001
    assert abs(lng - (-80.0)) < 0.001


def test_curved_geometry_snapping():
    """26. Snaps to polyline vertex on a curved polyline instead of straight-line endpoint interpolation."""
    # Symmetric curve: start at (-10.0, 0.0), curve peak at (0.0, 10.0), end at (10.0, 0.0)
    coords = [[-10.0, 0.0], [0.0, 10.0], [10.0, 0.0]]
    lat, lng = interpolate_polyline_coordinate(coords, 0.5)
    # Vertex is at (0.0, 10.0). Linear endpoint interpolation between (-10, 0) and (10, 0) would give (0.0, 0.0).
    assert abs(lat - 0.0) < 0.001
    assert abs(lng - 10.0) < 0.001


def test_empty_geometry_fallback():
    """27. Falls back to straight-line interpolation between start_loc and end_loc when geometry is missing."""
    start_loc = {"lat": 40.0, "lng": -90.0}
    end_loc = {"lat": 50.0, "lng": -90.0}

    lat, lng = interpolate_polyline_coordinate([], 0.5, start_loc, end_loc)
    assert abs(lat - 45.0) < 0.001
    assert abs(lng - (-90.0)) < 0.001

    lat2, lng2 = interpolate_polyline_coordinate(None, 0.5, start_loc, end_loc)
    assert abs(lat2 - 45.0) < 0.001
    assert abs(lng2 - (-90.0)) < 0.001


def test_generated_stop_uses_route_geometry(sample_locations):
    """28. Generated HOS 30m break stop waypoint uses route polyline geometry coordinates."""
    scheduler = HOSScheduler(
        current_location=sample_locations["chicago"],
        pickup_location=sample_locations["chicago"],
        dropoff_location=sample_locations["dallas"],
        current_cycle_used=0.0,
        start_datetime=datetime(2026, 8, 25, 8, 0)
    )

    curved_coords = [[-10.0, 0.0], [0.0, 10.0], [10.0, 0.0]]
    seg1 = {"distance_miles": 0.0, "duration_hours": 0.0, "coordinates": []}
    seg2 = {"distance_miles": 500.0, "duration_hours": 10.0, "coordinates": curved_coords}

    scheduler.generate_schedule(seg1, seg2)

    break_waypoints = [wp for wp in scheduler.waypoints if wp.waypoint_type == "REST_30M"]
    assert len(break_waypoints) >= 1

    break_wp = break_waypoints[0]
    # 8h break occurs at 80% of the 10h segment.
    # 80% along curved_coords (-10,0 -> 0,10 -> 10,0) puts it on segment 2 of the curve (lat > 0, lng > 0)
    # If endpoint linear interpolation had been used, lat would be -10 + 0.8 * 20 = +6.0, lng would be 0.0.
    # With curve snapping, lng is > 0 on segment 2.
    assert break_wp.lng > 0.0


def test_zero_distance_trip_timeline(sample_locations):
    """29. Zero-distance trip (Origin == Pickup == Dropoff) generates valid timeline with no driving."""
    scheduler = HOSScheduler(
        current_location=sample_locations["chicago"],
        pickup_location=sample_locations["chicago"],
        dropoff_location=sample_locations["chicago"],
        current_cycle_used=10.0,
        start_datetime=datetime(2026, 8, 25, 8, 0)
    )

    seg1 = {"distance_miles": 0.0, "duration_hours": 0.0}
    seg2 = {"distance_miles": 0.0, "duration_hours": 0.0}

    events = scheduler.generate_schedule(seg1, seg2)

    # Must contain 0 driving events
    drive_events = [ev for ev in events if ev.status == DutyStatus.D]
    assert len(drive_events) == 0

    # Must contain Pickup (1h ON) and Dropoff (1h ON)
    on_events = [ev for ev in events if ev.status == DutyStatus.ON]
    assert len(on_events) == 2
    assert "Pickup" in on_events[0].description
    assert "Dropoff" in on_events[1].description

    # Daily log partitioning must yield exactly 24.0 hours for Day 1
    daily_logs = partition_events_by_day(events)
    assert len(daily_logs) == 1
    summary = daily_logs[0]["summary"]
    total = summary["off_duty"] + summary["sleeper_berth"] + summary["driving"] + summary["on_duty"]
    assert round(total, 2) == 24.0


def test_very_long_trip_multiple_34h_restarts(sample_locations):
    """30. Multi-thousand mile trip triggering multiple 34h cycle restarts completes chronologically."""
    scheduler = HOSScheduler(
        current_location=sample_locations["chicago"],
        pickup_location=sample_locations["chicago"],
        dropoff_location=sample_locations["los_angeles"],
        current_cycle_used=65.0,
        start_datetime=datetime(2026, 8, 25, 8, 0)
    )

    # 9,000 miles, ~150 hours of driving to ensure multiple 70-hour cycle exhaustions
    seg1 = {"distance_miles": 0.0, "duration_hours": 0.0}
    seg2 = {"distance_miles": 9000.0, "duration_hours": 150.0}

    events = scheduler.generate_schedule(seg1, seg2)

    restart_events = [ev for ev in events if "34-Hour" in ev.description]
    assert len(restart_events) >= 2

    # Verify strict monotonic timestamp ordering across all events
    for i in range(1, len(events)):
        assert events[i].start_time >= events[i - 1].end_time

    # Verify daily log partitioning covers all days with exact 24.0h summaries
    daily_logs = partition_events_by_day(events)
    assert len(daily_logs) >= 8
    for log in daily_logs:
        summary = log["summary"]
        total = summary["off_duty"] + summary["sleeper_berth"] + summary["driving"] + summary["on_duty"]
        assert round(total, 2) == 24.0


def test_zero_distance_trip_with_initial_cycle_restart(sample_locations):
    """31. Zero-distance trip starting with 70.0h cycle used inserts initial 34h restart then pickup/dropoff."""
    scheduler = HOSScheduler(
        current_location=sample_locations["chicago"],
        pickup_location=sample_locations["chicago"],
        dropoff_location=sample_locations["chicago"],
        current_cycle_used=70.0,
        start_datetime=datetime(2026, 8, 25, 8, 0)
    )

    seg1 = {"distance_miles": 0.0, "duration_hours": 0.0}
    seg2 = {"distance_miles": 0.0, "duration_hours": 0.0}

    events = scheduler.generate_schedule(seg1, seg2)

    assert events[0].status == DutyStatus.OFF
    assert events[0].duration_hours == 34.0
    assert "34-Hour" in events[0].description

    daily_logs = partition_events_by_day(events)
    for log in daily_logs:
        summary = log["summary"]
        total = summary["off_duty"] + summary["sleeper_berth"] + summary["driving"] + summary["on_duty"]
        assert round(total, 2) == 24.0


@pytest.mark.django_db
def test_api_zero_distance_same_location():
    """32. API successfully handles zero-distance trip where origin, pickup, and dropoff are identical."""
    client = APIClient()

    response = client.post(
        "/api/plan-trip/",
        {
            "current_location": "Chicago, IL",
            "pickup_location": "Chicago, IL",
            "dropoff_location": "Chicago, IL",
            "current_cycle_used": 10.0
        },
        format="json"
    )

    assert response.status_code == 200
    res_data = response.json()
    assert res_data["status"] == "success"
    assert res_data["summary"]["total_driving_hours"] == 0.0
    assert len(res_data["daily_logs"]) >= 1
    summary = res_data["daily_logs"][0]["summary"]
    total = summary["off_duty"] + summary["sleeper_berth"] + summary["driving"] + summary["on_duty"]
    assert round(total, 2) == 24.0


@pytest.mark.django_db
def test_api_exact_max_cycle_used_boundary():
    """33. API successfully handles boundary current_cycle_used = 70.0 hours by triggering 34h restart."""
    client = APIClient()

    response = client.post(
        "/api/plan-trip/",
        {
            "current_location": "Chicago, IL",
            "pickup_location": "Indianapolis, IN",
            "dropoff_location": "Dallas, TX",
            "current_cycle_used": 70.0
        },
        format="json"
    )

    assert response.status_code == 200
    res_data = response.json()
    assert res_data["status"] == "success"
    assert len(res_data["daily_logs"]) >= 2