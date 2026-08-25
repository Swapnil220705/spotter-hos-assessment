from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import List, Dict, Any, Tuple

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

class HOSScheduler:
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
        
        # Default start time: 08:00 AM on today's date or supplied date
        if start_datetime is None:
            now = datetime.now()
            self.current_time = datetime(now.year, now.month, now.day, 8, 0, 0)
        else:
            self.current_time = start_datetime

        # HOS Tracking Accumulators
        self.drive_since_last_break = 0.0   # Towards 8h break
        self.drive_in_current_shift = 0.0   # Towards 11h drive limit
        self.shift_start_time = self.current_time  # Towards 14h window limit
        self.miles_since_last_fuel = 0.0    # Towards 1,000m fuel stop

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

        # Update on-duty cycle accumulator for ON and D statuses
        if status in [DutyStatus.ON, DutyStatus.D]:
            self.cycle_hours_used += duration_hours

    def _check_and_insert_restart(self, location_name: str, lat: float, lng: float):
        """Inserts a 34-hour restart if current 70-hour cycle limit is reached or exceeded."""
        if self.cycle_hours_used >= 70.0:
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
            # Reset cycle and shift trackers
            self.cycle_hours_used = 0.0
            self.drive_in_current_shift = 0.0
            self.drive_since_last_break = 0.0
            self.shift_start_time = self.current_time

    def _check_and_insert_rest(self, location_name: str, lat: float, lng: float):
        """Inserts a 10-hour mandatory rest break."""
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
        # Reset shift trackers after 10 consecutive hours rest
        self.drive_in_current_shift = 0.0
        self.drive_since_last_break = 0.0
        self.shift_start_time = self.current_time

    def _check_and_insert_30m_break(self, location_name: str, lat: float, lng: float):
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

    def _check_and_insert_fuel_stop(self, location_name: str, lat: float, lng: float):
        """Inserts a 30-minute fuel stop (On Duty Not Driving)."""
        self._add_event(
            status=DutyStatus.ON,
            duration_hours=0.5,
            location_name=location_name,
            lat=lat,
            lng=lng,
            description="Fueling Stop (1,000-Mile Requirement)"
        )
        self.waypoints.append(RouteWaypoint(
            waypoint_type="FUEL",
            name=location_name,
            lat=lat,
            lng=lng,
            time_str=self.current_time.strftime("%Y-%m-%d %H:%M")
        ))
        self.miles_since_last_fuel = 0.0

    def _simulate_driving_segment(
        self,
        segment_miles: float,
        start_loc: Dict[str, Any],
        end_loc: Dict[str, Any],
        segment_description: str
    ):
        """Simulates driving along a segment while enforcing HOS limits."""
        if segment_miles <= 0:
            return

        average_speed = 55.0  # mph
        remaining_miles = segment_miles
        start_lat, start_lng = start_loc["lat"], start_loc["lng"]
        end_lat, end_lng = end_loc["lat"], end_loc["lng"]

        # Step in maximum 0.5-hour driving chunks (~27.5 miles) to evaluate constraints smoothly
        chunk_time_limit = 0.5  # hours
        chunk_miles_limit = chunk_time_limit * average_speed

        miles_completed = 0.0

        while remaining_miles > 0:
            # Check 70-hour cycle restart requirement
            if self.cycle_hours_used >= 70.0:
                fraction = miles_completed / segment_miles if segment_miles > 0 else 0
                curr_lat = start_lat + (end_lat - start_lat) * fraction
                curr_lng = start_lng + (end_lng - start_lng) * fraction
                loc_label = f"En Route {segment_description}"
                self._check_and_insert_restart(loc_label, round(curr_lat, 4), round(curr_lng, 4))
                continue

            # Calculate current shift elapsed time
            shift_elapsed = (self.current_time - self.shift_start_time).total_seconds() / 3600.0
            remaining_14h_window = max(0.0, 14.0 - shift_elapsed)
            remaining_11h_drive = max(0.0, 11.0 - self.drive_in_current_shift)
            remaining_8h_break = max(0.0, 8.0 - self.drive_since_last_break)

            # If 11h drive or 14h window limit is exhausted, insert 10h rest
            if remaining_11h_drive <= 0.05 or remaining_14h_window <= 0.05:
                fraction = miles_completed / segment_miles if segment_miles > 0 else 0
                curr_lat = start_lat + (end_lat - start_lat) * fraction
                curr_lng = start_lng + (end_lng - start_lng) * fraction
                loc_label = f"Rest Stop ({segment_description})"
                self._check_and_insert_rest(loc_label, round(curr_lat, 4), round(curr_lng, 4))
                continue

            # If 8h drive limit before break is exhausted, insert 30m break
            if remaining_8h_break <= 0.05:
                fraction = miles_completed / segment_miles if segment_miles > 0 else 0
                curr_lat = start_lat + (end_lat - start_lat) * fraction
                curr_lng = start_lng + (end_lng - start_lng) * fraction
                loc_label = f"Break Stop ({segment_description})"
                self._check_and_insert_30m_break(loc_label, round(curr_lat, 4), round(curr_lng, 4))
                continue

            # Check 1,000-mile fuel stop requirement
            if self.miles_since_last_fuel >= 1000.0:
                fraction = miles_completed / segment_miles if segment_miles > 0 else 0
                curr_lat = start_lat + (end_lat - start_lat) * fraction
                curr_lng = start_lng + (end_lng - start_lng) * fraction
                loc_label = f"Fuel Station ({segment_description})"
                self._check_and_insert_fuel_stop(loc_label, round(curr_lat, 4), round(curr_lng, 4))
                continue

            # Determine maximum drive time allowed in this step
            max_drive_hours = min(
                chunk_time_limit,
                remaining_11h_drive,
                remaining_14h_window,
                remaining_8h_break,
                (70.0 - self.cycle_hours_used) if self.cycle_hours_used < 70.0 else 0.5,
                remaining_miles / average_speed
            )

            if max_drive_hours <= 0.01:
                # Force constraint check
                max_drive_hours = 0.01

            step_miles = min(remaining_miles, max_drive_hours * average_speed)
            actual_drive_hours = step_miles / average_speed

            # Drive this chunk
            miles_completed += step_miles
            remaining_miles -= step_miles

            fraction = miles_completed / segment_miles if segment_miles > 0 else 1.0
            curr_lat = start_lat + (end_lat - start_lat) * fraction
            curr_lng = start_lng + (end_lng - start_lng) * fraction

            self._add_event(
                status=DutyStatus.D,
                duration_hours=actual_drive_hours,
                location_name=f"En Route ({segment_description})",
                lat=round(curr_lat, 4),
                lng=round(curr_lng, 4),
                description=f"Driving towards destination",
                miles_driven=step_miles
            )

            # Update accumulators
            self.drive_in_current_shift += actual_drive_hours
            self.drive_since_last_break += actual_drive_hours
            self.miles_since_last_fuel += step_miles

    def generate_schedule(
        self,
        segment1_route: Dict[str, Any],
        segment2_route: Dict[str, Any]
    ) -> List[HOSEvent]:
        """Runs full HOS trip simulation across origin -> pickup -> dropoff."""
        
        # 1. Initial 34-hour restart if initial cycle hours used >= 70
        self._check_and_insert_restart(self.origin["name"], self.origin["lat"], self.origin["lng"])

        # 2. Drive Segment 1: Origin -> Pickup
        seg1_miles = segment1_route.get("distance_miles", 0.0)
        if seg1_miles > 0:
            self._simulate_driving_segment(
                segment_miles=seg1_miles,
                start_loc=self.origin,
                end_loc=self.pickup,
                segment_description=f"to {self.pickup['name']}"
            )

        # 3. Arrive at Pickup Location (1.0 Hour ON DUTY NOT DRIVING)
        self.waypoints.append(RouteWaypoint(
            waypoint_type="PICKUP",
            name=self.pickup["name"],
            lat=self.pickup["lat"],
            lng=self.pickup["lng"],
            time_str=self.current_time.strftime("%Y-%m-%d %H:%M")
        ))
        
        # Check if 14h window permits 1h pickup or if rest/restart is needed first
        shift_elapsed = (self.current_time - self.shift_start_time).total_seconds() / 3600.0
        if shift_elapsed + 1.0 > 14.0:
            self._check_and_insert_rest(self.pickup["name"], self.pickup["lat"], self.pickup["lng"])

        self._check_and_insert_restart(self.pickup["name"], self.pickup["lat"], self.pickup["lng"])

        self._add_event(
            status=DutyStatus.ON,
            duration_hours=1.0,
            location_name=self.pickup["name"],
            lat=self.pickup["lat"],
            lng=self.pickup["lng"],
            description="Pickup Work (Loading Cargo)"
        )

        # 4. Drive Segment 2: Pickup -> Dropoff
        seg2_miles = segment2_route.get("distance_miles", 0.0)
        if seg2_miles > 0:
            self._simulate_driving_segment(
                segment_miles=seg2_miles,
                start_loc=self.pickup,
                end_loc=self.dropoff,
                segment_description=f"to {self.dropoff['name']}"
            )

        # 5. Arrive at Dropoff Location (1.0 Hour ON DUTY NOT DRIVING)
        shift_elapsed = (self.current_time - self.shift_start_time).total_seconds() / 3600.0
        if shift_elapsed + 1.0 > 14.0:
            self._check_and_insert_rest(self.dropoff["name"], self.dropoff["lat"], self.dropoff["lng"])

        self._check_and_insert_restart(self.dropoff["name"], self.dropoff["lat"], self.dropoff["lng"])

        self.waypoints.append(RouteWaypoint(
            waypoint_type="DROPOFF",
            name=self.dropoff["name"],
            lat=self.dropoff["lat"],
            lng=self.dropoff["lng"],
            time_str=self.current_time.strftime("%Y-%m-%d %H:%M")
        ))

        self._add_event(
            status=DutyStatus.ON,
            duration_hours=1.0,
            location_name=self.dropoff["name"],
            lat=self.dropoff["lat"],
            lng=self.dropoff["lng"],
            description="Dropoff Work (Unloading Cargo)"
        )

        return self.events
