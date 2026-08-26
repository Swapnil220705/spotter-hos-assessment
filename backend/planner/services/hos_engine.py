from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import List, Dict, Any, Tuple
from .routing import haversine_distance_miles

class DutyStatus:
    OFF = "OFF"     # Off Duty
    SB = "SB"       # Sleeper Berth
    D = "D"         # Driving
    ON = "ON"       # On Duty (Not Driving)

@dataclass
class HOSEvent:
    status: str
    start_time: datetime
    end_time: datetime
    duration_hours: float
    location_name: str
    lat: float
    lng: float
    description: str
    miles_driven: float = 0.0

@dataclass
class RouteWaypoint:
    waypoint_type: str  # ORIGIN, PICKUP, DROPOFF, FUEL, REST_30M, REST_10H, RESTART_34H
    name: str
    lat: float
    lng: float
    time_str: str = ""

def format_location_remark(event: HOSEvent) -> Dict[str, Any]:
    """Formats an HOSEvent into a location-stamped remark entry."""
    return {
        "time": event.start_time.strftime("%H:%M"),
        "location": event.location_name,
        "status": event.status,
        "note": event.description,
        "miles": round(event.miles_driven, 1)
    }

def interpolate_polyline_coordinate(
    coordinates: List[List[float]],
    fraction: float,
    start_loc: Dict[str, Any] = None,
    end_loc: Dict[str, Any] = None
) -> Tuple[float, float]:
    """
    Interpolates a [lat, lng] coordinate along a polyline geometry at a given distance fraction (0.0 to 1.0).
    Uses cumulative Haversine distance along the polyline.
    Falls back to straight-line interpolation between start_loc and end_loc if coordinates is empty or invalid.
    """
    fraction = max(0.0, min(1.0, fraction))

    if not coordinates or len(coordinates) < 2:
        if start_loc and end_loc:
            start_lat, start_lng = start_loc["lat"], start_loc["lng"]
            end_lat, end_lng = end_loc["lat"], end_loc["lng"]
            lat = start_lat + (end_lat - start_lat) * fraction
            lng = start_lng + (end_lng - start_lng) * fraction
            return (lat, lng)
        return (0.0, 0.0)

    if fraction <= 0.0:
        return (coordinates[0][0], coordinates[0][1])
    if fraction >= 1.0:
        return (coordinates[-1][0], coordinates[-1][1])

    segment_lengths = []
    total_length = 0.0
    for i in range(len(coordinates) - 1):
        p1 = coordinates[i]
        p2 = coordinates[i + 1]
        dist = haversine_distance_miles(p1[0], p1[1], p2[0], p2[1])
        segment_lengths.append(dist)
        total_length += dist

    if total_length <= 0.0001:
        return (coordinates[0][0], coordinates[0][1])

    target_dist = fraction * total_length
    accumulated_dist = 0.0

    for i, seg_len in enumerate(segment_lengths):
        if accumulated_dist + seg_len >= target_dist:
            seg_fraction = (target_dist - accumulated_dist) / seg_len if seg_len > 0 else 0.0
            p1 = coordinates[i]
            p2 = coordinates[i + 1]
            lat = p1[0] + (p2[0] - p1[0]) * seg_fraction
            lng = p1[1] + (p2[1] - p1[1]) * seg_fraction
            return (lat, lng)
        accumulated_dist += seg_len

    return (coordinates[-1][0], coordinates[-1][1])

class HOSScheduler:
    """
    Pure Python HOS Scheduler implementing FMCSA Property-Carrier Rules.
    Independently tracks:
    - 11-hour shift driving limit
    - 14-hour duty window limit
    - 70-hour / 8-day rolling cycle limit
    - 8-hour cumulative driving limit prior to 30-minute break
    - 1,000-mile fueling requirement (30-min ON-duty assumption)
    """

    def __init__(
        self,
        current_location: Dict[str, Any],
        pickup_location: Dict[str, Any],
        dropoff_location: Dict[str, Any],
        current_cycle_used: float = 0.0,
        start_datetime: datetime = None
    ):
        self.origin = current_location
        self.pickup = pickup_location
        self.dropoff = dropoff_location
        self.cycle_hours_used = float(current_cycle_used)

        # Implementation Assumption: Default trip start time is 08:00 AM
        if start_datetime is None:
            now = datetime.now()
            self.current_time = datetime(now.year, now.month, now.day, 8, 0, 0)
        else:
            self.current_time = start_datetime

        # Independent HOS Trackers
        self.drive_in_current_shift = 0.0       # Towards 11h driving limit
        self.shift_start_time = self.current_time  # Towards 14h window limit
        self.drive_since_last_break = 0.0       # Towards 8h driving break
        self.miles_since_last_fuel = 0.0        # Towards 1,000m fuel stop

        self.events: List[HOSEvent] = []
        self.waypoints: List[RouteWaypoint] = []

        # Add initial origin waypoint
        self.waypoints.append(RouteWaypoint(
            waypoint_type="ORIGIN",
            name=self.origin["name"],
            lat=self.origin["lat"],
            lng=self.origin["lng"],
            time_str=self.current_time.strftime("%Y-%m-%d %H:%M")
        ))

    def _add_event(
        self,
        status: str,
        duration_hours: float,
        location_name: str,
        lat: float,
        lng: float,
        description: str,
        miles_driven: float = 0.0
    ):
        """Helper to append an event and update current simulation clock."""
        start = self.current_time
        end = start + timedelta(hours=duration_hours)
        event = HOSEvent(
            status=status,
            start_time=start,
            end_time=end,
            duration_hours=round(duration_hours, 2),
            location_name=location_name,
            lat=lat,
            lng=lng,
            description=description,
            miles_driven=round(miles_driven, 1)
        )
        self.events.append(event)
        self.current_time = end

    def _insert_34h_restart(self, location_name: str, lat: float, lng: float):
        """Inserts a 34-hour off-duty cycle restart."""
        self._add_event(
            status=DutyStatus.OFF,
            duration_hours=34.0,
            location_name=location_name,
            lat=lat,
            lng=lng,
            description="34-Hour Off-Duty Cycle Restart"
        )
        self.waypoints.append(RouteWaypoint(
            waypoint_type="RESTART_34H",
            name=location_name,
            lat=lat,
            lng=lng,
            time_str=self.current_time.strftime("%Y-%m-%d %H:%M")
        ))
        # Reset cycle, shift, and break trackers
        self.cycle_hours_used = 0.0
        self.drive_in_current_shift = 0.0
        self.drive_since_last_break = 0.0
        self.shift_start_time = self.current_time

    def _insert_10h_rest(self, location_name: str, lat: float, lng: float):
        """Inserts a 10-hour mandatory off-duty rest period."""
        self._add_event(
            status=DutyStatus.OFF,
            duration_hours=10.0,
            location_name=location_name,
            lat=lat,
            lng=lng,
            description="10-Hour Mandatory Rest Period"
        )
        self.waypoints.append(RouteWaypoint(
            waypoint_type="REST_10H",
            name=location_name,
            lat=lat,
            lng=lng,
            time_str=self.current_time.strftime("%Y-%m-%d %H:%M")
        ))
        # Reset shift driving, break, and window trackers
        self.drive_in_current_shift = 0.0
        self.drive_since_last_break = 0.0
        self.shift_start_time = self.current_time

    def _insert_30m_break(self, location_name: str, lat: float, lng: float):
        """Inserts a required 30-minute break."""
        self._add_event(
            status=DutyStatus.OFF,
            duration_hours=0.5,
            location_name=location_name,
            lat=lat,
            lng=lng,
            description="30-Minute Rest Break (8-Hour Driving Rule)"
        )
        self.waypoints.append(RouteWaypoint(
            waypoint_type="REST_30M",
            name=location_name,
            lat=lat,
            lng=lng,
            time_str=self.current_time.strftime("%Y-%m-%d %H:%M")
        ))
        self.drive_since_last_break = 0.0

    def _handle_on_duty_task(
        self,
        task_name: str,
        duration_hours: float,
        location: Dict[str, Any],
        waypoint_type: str = None
    ):
        """
        Handles an ON-duty non-driving task (Pickup 1h, Dropoff 1h, Fueling 0.5h, etc.).
        Verifies 14-hour window and 70-hour cycle constraints BEFORE starting work.
        Note: The 11-hour driving limit does NOT restrict ON-duty non-driving work.
        """
        loc_name = location["name"]
        lat = location["lat"]
        lng = location["lng"]

        # Check 70-hour cycle limit
        if self.cycle_hours_used + duration_hours > 70.0 or self.cycle_hours_used >= 70.0:
            self._insert_34h_restart(loc_name, lat, lng)

        # Check 14-hour duty window limit
        shift_elapsed = (self.current_time - self.shift_start_time).total_seconds() / 3600.0
        if shift_elapsed + duration_hours > 14.0:
            self._insert_10h_rest(loc_name, lat, lng)
            # Re-check 70h cycle after 10h rest if needed
            if self.cycle_hours_used + duration_hours > 70.0:
                self._insert_34h_restart(loc_name, lat, lng)

        if waypoint_type:
            self.waypoints.append(RouteWaypoint(
                waypoint_type=waypoint_type,
                name=loc_name,
                lat=lat,
                lng=lng,
                time_str=self.current_time.strftime("%Y-%m-%d %H:%M")
            ))

        desc = task_name if ("Work" in task_name or "Stop" in task_name) else f"{task_name} Work"

        self._add_event(
            status=DutyStatus.ON,
            duration_hours=duration_hours,
            location_name=loc_name,
            lat=lat,
            lng=lng,
            description=desc
        )
        self.cycle_hours_used += duration_hours

        # Consecutive non-driving work >= 30 mins resets 30m break tracker
        if duration_hours >= 0.5:
            self.drive_since_last_break = 0.0

    def _insert_fuel_stop(self, location_name: str, lat: float, lng: float):
        """
        Inserts a 30-minute fuel stop (On Duty Not Driving).
        Delegates to _handle_on_duty_task to enforce 14-hour window and 70-hour cycle
        checks BEFORE starting fueling work.
        """
        location = {"name": location_name, "lat": lat, "lng": lng}
        self._handle_on_duty_task(
            task_name="Fueling Stop (1,000-Mile Requirement)",
            duration_hours=0.5,
            location=location,
            waypoint_type="FUEL"
        )
        self.miles_since_last_fuel = 0.0

    def _simulate_driving_segment(
        self,
        segment_miles: float,
        segment_duration_hours: float,
        start_loc: Dict[str, Any],
        end_loc: Dict[str, Any],
        segment_description: str,
        coordinates: List[List[float]] = None
    ):
        """Simulates driving along a segment while enforcing all driving constraints."""
        if segment_miles <= 0 or segment_duration_hours <= 0:
            return

        effective_speed = segment_miles / segment_duration_hours
        remaining_miles = segment_miles
        remaining_hours = segment_duration_hours

        while remaining_miles > 0.001 or remaining_hours > 0.001:
            shift_elapsed = (self.current_time - self.shift_start_time).total_seconds() / 3600.0

            rem_11h_drive = max(0.0, 11.0 - self.drive_in_current_shift)
            rem_14h_window = max(0.0, 14.0 - shift_elapsed)
            rem_8h_break = max(0.0, 8.0 - self.drive_since_last_break)
            rem_70h_cycle = max(0.0, 70.0 - self.cycle_hours_used)

            rem_fuel_miles = max(0.0, 1000.0 - self.miles_since_last_fuel)
            rem_fuel_hours = rem_fuel_miles / effective_speed if effective_speed > 0 else 18.18

            # Calculate earliest constraint boundary
            max_drive_hours = min(
                remaining_hours,
                rem_11h_drive,
                rem_14h_window,
                rem_8h_break,
                rem_70h_cycle,
                rem_fuel_hours
            )

            if max_drive_hours > 0.001:
                step_miles = min(remaining_miles, max_drive_hours * effective_speed)
                step_hours = step_miles / effective_speed if effective_speed > 0 else max_drive_hours

                # Interpolate intermediate position along segment
                miles_completed = segment_miles - remaining_miles + step_miles
                fraction = min(1.0, miles_completed / segment_miles) if segment_miles > 0 else 1.0
                curr_lat, curr_lng = interpolate_polyline_coordinate(
                    coordinates=coordinates,
                    fraction=fraction,
                    start_loc=start_loc,
                    end_loc=end_loc
                )

                self._add_event(
                    status=DutyStatus.D,
                    duration_hours=step_hours,
                    location_name=f"En Route ({segment_description})",
                    lat=round(curr_lat, 4),
                    lng=round(curr_lng, 4),
                    description="Driving towards destination",
                    miles_driven=step_miles
                )

                remaining_miles -= step_miles
                remaining_hours -= step_hours
                self.drive_in_current_shift += step_hours
                self.drive_since_last_break += step_hours
                self.cycle_hours_used += step_hours
                self.miles_since_last_fuel += step_miles

            # If more driving remains for this segment, handle the constraint that was hit
            if remaining_miles > 0.001 or remaining_hours > 0.001:
                fraction = min(1.0, (segment_miles - remaining_miles) / segment_miles) if segment_miles > 0 else 0.0
                curr_lat, curr_lng = interpolate_polyline_coordinate(
                    coordinates=coordinates,
                    fraction=fraction,
                    start_loc=start_loc,
                    end_loc=end_loc
                )

                # Evaluate constraints in priority order:
                # 1. 70-Hour Cycle Exhaustion -> 34h Restart
                if self.cycle_hours_used >= 70.0:
                    self._insert_34h_restart(
                        f"En Route {segment_description}",
                        round(curr_lat, 4),
                        round(curr_lng, 4)
                    )
                # 2. 11h Drive Limit or 14h Duty Window -> 10h Rest
                elif self.drive_in_current_shift >= 11.0 or (self.current_time - self.shift_start_time).total_seconds() / 3600.0 >= 14.0:
                    self._insert_10h_rest(
                        f"Rest Stop ({segment_description})",
                        round(curr_lat, 4),
                        round(curr_lng, 4)
                    )
                # 3. 8h Cumulative Drive Break -> 30m Break
                elif self.drive_since_last_break >= 8.0:
                    self._insert_30m_break(
                        f"Break Stop ({segment_description})",
                        round(curr_lat, 4),
                        round(curr_lng, 4)
                    )
                # 4. 1,000-Mile Fueling Requirement -> 30m Fuel Stop (ON Duty)
                elif self.miles_since_last_fuel >= 1000.0:
                    self._insert_fuel_stop(
                        f"Fuel Station ({segment_description})",
                        round(curr_lat, 4),
                        round(curr_lng, 4)
                    )

    def generate_schedule(
        self,
        segment1_route: Dict[str, Any],
        segment2_route: Dict[str, Any]
    ) -> List[HOSEvent]:
        """Runs full HOS trip simulation across origin -> pickup -> dropoff."""

        # 1. Handle Initial 70h Cycle Restart if current_cycle_used >= 70
        if self.cycle_hours_used >= 70.0:
            self._insert_34h_restart(self.origin["name"], self.origin["lat"], self.origin["lng"])

        # 2. Drive Segment 1: Origin -> Pickup
        seg1_miles = segment1_route.get("distance_miles", 0.0)
        seg1_hours = segment1_route.get("duration_hours", 0.0)
        seg1_coords = segment1_route.get("coordinates", [])
        if seg1_miles > 0 and seg1_hours > 0:
            self._simulate_driving_segment(
                segment_miles=seg1_miles,
                segment_duration_hours=seg1_hours,
                start_loc=self.origin,
                end_loc=self.pickup,
                segment_description=f"to {self.pickup['name']}",
                coordinates=seg1_coords
            )

        # 3. Arrive at Pickup Location & Execute 1.0 Hour ON DUTY Pickup Work
        self._handle_on_duty_task(
            task_name="Pickup (Loading Cargo)",
            duration_hours=1.0,
            location=self.pickup,
            waypoint_type="PICKUP"
        )

        # 4. Drive Segment 2: Pickup -> Dropoff
        seg2_miles = segment2_route.get("distance_miles", 0.0)
        seg2_hours = segment2_route.get("duration_hours", 0.0)
        seg2_coords = segment2_route.get("coordinates", [])
        if seg2_miles > 0 and seg2_hours > 0:
            self._simulate_driving_segment(
                segment_miles=seg2_miles,
                segment_duration_hours=seg2_hours,
                start_loc=self.pickup,
                end_loc=self.dropoff,
                segment_description=f"to {self.dropoff['name']}",
                coordinates=seg2_coords
            )

        # 5. Arrive at Dropoff Location & Execute 1.0 Hour ON DUTY Dropoff Work
        self._handle_on_duty_task(
            task_name="Dropoff (Unloading Cargo)",
            duration_hours=1.0,
            location=self.dropoff,
            waypoint_type="DROPOFF"
        )

        return self.events
