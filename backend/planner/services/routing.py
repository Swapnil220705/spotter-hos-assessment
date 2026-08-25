import math
import requests
from typing import Dict, Any, List, Tuple

def haversine_distance_miles(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Computes straight-line distance in miles between two coordinates."""
    R = 3958.8  # Earth radius in miles
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (math.sin(dlat / 2) ** 2 +
         math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2) ** 2)
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c

def interpolate_points(coord1: Tuple[float, float], coord2: Tuple[float, float], num_points: int = 20) -> List[List[float]]:
    """Generates interpolated [lat, lng] coordinates between two points."""
    lat1, lng1 = coord1
    lat2, lng2 = coord2
    points = []
    for i in range(num_points + 1):
        fraction = i / num_points
        lat = lat1 + (lat2 - lat1) * fraction
        lng = lng1 + (lng2 - lng1) * fraction
        points.append([round(lat, 5), round(lng, 5)])
    return points

def get_route_segment(origin: Dict[str, Any], destination: Dict[str, Any]) -> Dict[str, Any]:
    """
    Fetches driving distance, duration, and geometry polyline for a single segment (A to B) using OSRM.
    Uses actual OSRM duration_seconds converted to hours.
    Falls back to Haversine calculation at 55 mph if OSRM API is offline or unavailable.
    """
    lat1, lng1 = origin["lat"], origin["lng"]
    lat2, lng2 = destination["lat"], destination["lng"]

    url = f"http://router.project-osrm.org/route/v1/driving/{lng1},{lat1};{lng2},{lat2}?overview=full&geometries=geojson"

    try:
        response = requests.get(url, timeout=6)
        if response.status_code == 200:
            data = response.json()
            if data.get("routes") and len(data["routes"]) > 0:
                route = data["routes"][0]
                distance_meters = route.get("distance", 0)
                duration_seconds = route.get("duration", 0)
                geometry = route.get("geometry", {}).get("coordinates", [])

                # OSRM returns coordinates as [lng, lat], convert to [lat, lng]
                lat_lng_coords = [[coord[1], coord[0]] for coord in geometry]

                distance_miles = distance_meters * 0.000621371

                # Use actual OSRM duration in hours when available
                if duration_seconds > 0:
                    driving_hours = duration_seconds / 3600.0
                elif distance_miles > 0:
                    driving_hours = distance_miles / 55.0
                else:
                    driving_hours = 0.0

                return {
                    "distance_miles": round(distance_miles, 1),
                    "duration_hours": round(driving_hours, 2),
                    "coordinates": lat_lng_coords if lat_lng_coords else interpolate_points((lat1, lng1), (lat2, lng2))
                }
    except Exception:
        pass

    # Fallback routing calculation (when OSRM is offline)
    direct_dist = haversine_distance_miles(lat1, lng1, lat2, lng2)
    road_dist = round(direct_dist * 1.25, 1)  # Estimate 1.25x road circuity factor
    driving_hours = round(road_dist / 55.0, 2) if road_dist > 0 else 0.0
    coords = interpolate_points((lat1, lng1), (lat2, lng2), num_points=30)

    return {
        "distance_miles": road_dist,
        "duration_hours": driving_hours,
        "coordinates": coords
    }
