from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from datetime import datetime

from .services.geocoding import geocode_location
from .services.routing import get_route_segment
from .services.hos_engine import HOSScheduler, DutyStatus
from .services.log_partitioner import partition_events_by_day

@api_view(['GET'])
def health_check(request):
    """Health check endpoint to verify backend service status."""
    return Response({
        "status": "healthy",
        "service": "Spotter HOS Planner API",
        "version": "1.0.0"
    })

@api_view(['POST'])
def plan_trip(request):
    """
    Main endpoint for trip planning & HOS ELD generation.
    Accepts trip locations & cycle hours used, returns route, stop waypoints, HOS schedule, and daily ELD logs.
    """
    data = request.data or {}
    
    current_loc_str = data.get("current_location", "").strip()
    pickup_loc_str = data.get("pickup_location", "").strip()
    dropoff_loc_str = data.get("dropoff_location", "").strip()
    cycle_used_raw = data.get("current_cycle_used", 0.0)

    # Input Validation
    if not current_loc_str or not pickup_loc_str or not dropoff_loc_str:
        return Response(
            {"error": "Missing required fields: current_location, pickup_location, and dropoff_location are required."},
            status=status.HTTP_400_BAD_REQUEST
        )

    try:
        current_cycle_used = float(cycle_used_raw)
        if current_cycle_used < 0 or current_cycle_used > 70:
            return Response(
                {"error": "Invalid current_cycle_used value. Must be between 0 and 70 hours."},
                status=status.HTTP_400_BAD_REQUEST
            )
    except (ValueError, TypeError):
        return Response(
            {"error": "current_cycle_used must be a numeric value."},
            status=status.HTTP_400_BAD_REQUEST
        )

    try:
        # 1. Geocode Locations
        origin_geo = geocode_location(current_loc_str)
        pickup_geo = geocode_location(pickup_loc_str)
        dropoff_geo = geocode_location(dropoff_loc_str)

        # 2. Get Route Data (OSRM)
        seg1 = get_route_segment(origin_geo, pickup_geo)
        seg2 = get_route_segment(pickup_geo, dropoff_geo)

        # 3. Run HOS Scheduler Engine
        scheduler = HOSScheduler(
            current_location=origin_geo,
            pickup_location=pickup_geo,
            dropoff_location=dropoff_geo,
            current_cycle_used=current_cycle_used
        )
        events = scheduler.generate_schedule(seg1, seg2)

        # 4. Partition Events by 24h Calendar Days
        daily_logs = partition_events_by_day(events)

        # Combine polyline coordinates for map
        combined_coords = seg1.get("coordinates", []) + seg2.get("coordinates", [])

        # Format route waypoints for map markers
        waypoints_data = [
            {
                "type": wp.waypoint_type,
                "name": wp.name,
                "lat": wp.lat,
                "lng": wp.lng,
                "time": wp.time_str
            }
            for wp in scheduler.waypoints
        ]

        total_distance = round(seg1.get("distance_miles", 0.0) + seg2.get("distance_miles", 0.0), 1)
        total_driving_hours = round(sum(ev.duration_hours for ev in events if ev.status == DutyStatus.D), 2)
        total_on_duty_hours = round(sum(ev.duration_hours for ev in events if ev.status == DutyStatus.ON), 2)
        total_rest_hours = round(sum(ev.duration_hours for ev in events if ev.status == DutyStatus.OFF), 2)
        total_elapsed_hours = round(sum(ev.duration_hours for ev in events), 2)

        return Response({
            "status": "success",
            "summary": {
                "total_distance_miles": total_distance,
                "total_driving_hours": total_driving_hours,
                "total_on_duty_hours": total_on_duty_hours,
                "total_rest_hours": total_rest_hours,
                "total_trip_hours": total_elapsed_hours,
                "total_days": len(daily_logs)
            },
            "route": {
                "coordinates": combined_coords,
                "waypoints": waypoints_data
            },
            "daily_logs": daily_logs
        }, status=status.HTTP_200_OK)

    except Exception:
        return Response(
            {"error": "An internal server error occurred while processing the trip plan."},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
