from datetime import datetime, timedelta
from typing import List, Dict, Any
from .hos_engine import HOSEvent, DutyStatus, format_location_remark

def partition_events_by_day(events: List[HOSEvent]) -> List[Dict[str, Any]]:
    """
    Takes a continuous chronological list of HOSEvents and partitions them
    into 24-hour calendar day buckets (00:00 to 24:00).
    Ensures that event status totals for every day sum to exactly 24.0 hours.
    """
    if not events:
        return []

    # Find earliest start date and latest end date
    start_date = events[0].start_time.date()
    end_date = events[-1].end_time.date()

    # Step through each calendar day
    daily_logs = []
    current_day_date = start_date
    day_number = 1

    while current_day_date <= end_date:
        day_start_dt = datetime(current_day_date.year, current_day_date.month, current_day_date.day, 0, 0, 0)
        day_end_dt = day_start_dt + timedelta(days=1)
        date_str = current_day_date.strftime("%Y-%m-%d")

        day_events: List[Dict[str, Any]] = []
        day_remarks: List[Dict[str, Any]] = []

        off_duty_hours = 0.0
        sleeper_berth_hours = 0.0
        driving_hours = 0.0
        on_duty_hours = 0.0
        day_miles = 0.0

        for ev in events:
            # Check overlap between event [ev.start_time, ev.end_time] and day [day_start_dt, day_end_dt]
            overlap_start = max(ev.start_time, day_start_dt)
            overlap_end = min(ev.end_time, day_end_dt)

            if overlap_start < overlap_end:
                duration_hrs = (overlap_end - overlap_start).total_seconds() / 3600.0

                # Proportional miles driven during this day slice
                total_ev_hrs = ev.duration_hours if ev.duration_hours > 0 else 0.01
                proportional_miles = (duration_hrs / total_ev_hrs) * ev.miles_driven if total_ev_hrs > 0 else 0.0
                day_miles += proportional_miles

                # Accumulate hours by status
                if ev.status == DutyStatus.OFF:
                    off_duty_hours += duration_hrs
                elif ev.status == DutyStatus.SB:
                    sleeper_berth_hours += duration_hrs
                elif ev.status == DutyStatus.D:
                    driving_hours += duration_hrs
                elif ev.status == DutyStatus.ON:
                    on_duty_hours += duration_hrs

                day_events.append({
                    "status": ev.status,
                    "start_time": overlap_start.strftime("%H:%M"),
                    "end_time": overlap_end.strftime("%H:%M") if overlap_end < day_end_dt else "24:00",
                    "duration_hours": round(duration_hrs, 2),
                    "location": ev.location_name,
                    "description": ev.description,
                    "miles_driven": round(proportional_miles, 1)
                })

                # Record remark if status change occurs on this day
                if overlap_start == ev.start_time:
                    day_remarks.append({
                        "time": overlap_start.strftime("%H:%M"),
                        "location": ev.location_name,
                        "status": ev.status,
                        "note": ev.description,
                        "miles": round(proportional_miles, 1)
                    })

        # If a day has no events explicitly (e.g. initial off-duty before trip starts), fill with OFF duty
        if not day_events:
            off_duty_hours = 24.0
            day_events.append({
                "status": DutyStatus.OFF,
                "start_time": "00:00",
                "end_time": "24:00",
                "duration_hours": 24.0,
                "location": events[0].location_name if events else "Home Terminal",
                "description": "Off Duty",
                "miles_driven": 0.0
            })
            day_remarks.append({
                "time": "00:00",
                "location": events[0].location_name if events else "Home Terminal",
                "status": DutyStatus.OFF,
                "note": "Off Duty All Day",
                "miles": 0.0
            })

        # Normalize and round total hours so their sum equals exactly 24.0
        off_duty_hours = round(off_duty_hours, 2)
        sleeper_berth_hours = round(sleeper_berth_hours, 2)
        driving_hours = round(driving_hours, 2)
        on_duty_hours = round(on_duty_hours, 2)

        total_sum = off_duty_hours + sleeper_berth_hours + driving_hours + on_duty_hours
        diff = round(24.0 - total_sum, 2)
        if abs(diff) > 0.0:
            # Adjust largest component or off-duty to maintain exact 24.0 balance
            off_duty_hours = round(off_duty_hours + diff, 2)

        daily_logs.append({
            "day_number": day_number,
            "date": date_str,
            "total_miles": round(day_miles, 1),
            "summary": {
                "off_duty": off_duty_hours,
                "sleeper_berth": sleeper_berth_hours,
                "driving": driving_hours,
                "on_duty": on_duty_hours,
                "total": 24.0
            },
            "events": day_events,
            "remarks": day_remarks
        })

        current_day_date += timedelta(days=1)
        day_number += 1

    return daily_logs
