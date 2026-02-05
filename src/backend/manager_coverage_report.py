"""
Manager coverage reporting utilities.

Provides functions to:
- filter shifts by date range and location
- compute fill status per shift
- compute participation rate per staff member
- export report to CSV string

This module is intentionally small and dependency-free so it can be imported
directly by backend.main and consumed by the frontend (via an API endpoint).
"""
from datetime import datetime
from typing import Dict, Iterable, List, Optional
import csv
import io


def _parse_date(value: Optional[object]) -> Optional[datetime]:
    """Parse a date-like value to a datetime, or return None."""
    if value is None:
        return None
    if isinstance(value, datetime):
        return value
    if isinstance(value, str):
        try:
            # Accept ISO 8601 like "YYYY-MM-DD" or full datetime
            return datetime.fromisoformat(value)
        except ValueError:
            # Fallback: try common date format
            try:
                return datetime.strptime(value, "%Y-%m-%d")
            except ValueError:
                return None
    return None


def filter_shifts(
    shifts: Iterable[Dict],
    start_date: Optional[object] = None,
    end_date: Optional[object] = None,
    location: Optional[str] = None,
) -> List[Dict]:
    """
    Return shifts filtered by an optional date range and location.

    Each shift dict is expected to contain at least:
      - 'id': any
      - 'date': ISO date string or datetime
      - 'location': string

    start_date and end_date may be strings (ISO), datetime, or None.
    Inclusive filtering is applied: start_date <= shift.date <= end_date.
    """
    start = _parse_date(start_date)
    end = _parse_date(end_date)
    result: List[Dict] = []
    for shift in shifts:
        shift_date = _parse_date(shift.get("date"))
        if shift_date is None:
            # Skip shifts without a valid date
            continue
        if start is not None and shift_date < start:
            continue
        if end is not None and shift_date > end:
            continue
        if location is not None and str(shift.get("location")) != str(location):
            continue
        result.append(shift.copy())
    return result


def _is_shift_filled(shift: Dict) -> bool:
    """
    Determine whether a shift is considered filled.

    Expects shift to have:
      - 'required_staff': int (defaults to 1)
      - 'assigned_staff': Iterable (defaults to empty)
    """
    required = shift.get("required_staff", 1)
    try:
        required_int = int(required)
    except Exception:  # pylint: disable=broad-except
        required_int = 1
    assigned = shift.get("assigned_staff") or []
    try:
        assigned_count = len(assigned)
    except Exception:  # pylint: disable=broad-except
        # assigned not sized; treat as not filled
        assigned_count = 0
    return assigned_count >= required_int


def shifts_with_fill_status(shifts: Iterable[Dict]) -> List[Dict]:
    """
    Annotate shifts with fill information.

    Returns list of shift dicts with added keys:
      - 'filled': bool
      - 'assigned_count': int
      - 'required_staff': int
      - 'date': ISO format string (if parsable)
    """
    enriched: List[Dict] = []
    for shift in shifts:
        s = shift.copy()
        date_obj = _parse_date(s.get("date"))
        if date_obj is not None:
            s["date"] = date_obj.date().isoformat()
        required = s.get("required_staff", 1)
        try:
            required_int = int(required)
        except Exception:  # pylint: disable=broad-except
            required_int = 1
        assigned = s.get("assigned_staff") or []
        try:
            assigned_count = len(assigned)
        except Exception:  # pylint: disable=broad-except
            assigned_count = 0
        s["required_staff"] = required_int
        s["assigned_count"] = assigned_count
        s["filled"] = assigned_count >= required_int
        enriched.append(s)
    return enriched


def participation_rate_by_staff(shifts: Iterable[Dict]) -> Dict[str, Dict[str, object]]:
    """
    Compute participation statistics per staff member.

    From the given shifts (already filtered to the desired set), count how many
    shifts each staff member was assigned to and compute a participation rate
    relative to the number of shifts considered.

    Returns dict keyed by staff identifier (string) with values:
      - 'assigned': int
      - 'rate': float (0..1)
    """
    counts: Dict[str, int] = {}
    total_shifts = 0
    for shift in shifts:
        total_shifts += 1
        assigned = shift.get("assigned_staff") or []
        for staff in assigned:
            staff_id = str(staff)
            counts[staff_id] = counts.get(staff_id, 0) + 1
    result: Dict[str, Dict[str, object]] = {}
    if total_shifts == 0:
        return result
    for staff_id, assigned_count in counts.items():
        rate = float(assigned_count) / float(total_shifts)
        result[staff_id] = {"assigned": assigned_count, "rate": rate}
    return result


def generate_report(
    shifts: Iterable[Dict],
    start_date: Optional[object] = None,
    end_date: Optional[object] = None,
    location: Optional[str] = None,
) -> Dict[str, object]:
    """
    Generate a coverage report dictionary.

    The report contains:
      - 'shifts': list of annotated shifts (see shifts_with_fill_status)
      - 'participation': per-staff participation stats (see participation_rate_by_staff)
      - 'total_shifts': int
      - 'filters': dict with the applied filters

    This function is intended to be called by the backend route handler.
    """
    filtered = filter_shifts(shifts, start_date=start_date, end_date=end_date, location=location)
    annotated = shifts_with_fill_status(filtered)
    participation = participation_rate_by_staff(filtered)
    report = {
        "shifts": annotated,
        "participation": participation,
        "total_shifts": len(annotated),
        "filters": {"start_date": start_date, "end_date": end_date, "location": location},
    }
    return report


def report_to_csv(report: Dict[str, object]) -> str:
    """
    Convert a report produced by generate_report to a CSV string.

    The CSV contains two sections separated by an empty line:
      1) Shifts table with columns: id, date, location, required_staff, assigned_count, filled
      2) Participation table with columns: staff_id, assigned, rate

    Returns a UTF-8 encoded string.
    """
    output = io.StringIO()
    writer = csv.writer(output)
    # Shifts section
    writer.writerow(["id", "date", "location", "required_staff", "assigned_count", "filled"])
    for shift in report.get("shifts", []):
        writer.writerow([
            shift.get("id", ""),
            shift.get("date", ""),
            shift.get("location", ""),
            shift.get("required_staff", ""),
            shift.get("assigned_count", ""),
            shift.get("filled", ""),
        ])
    # Blank line separator
    writer.writerow([])
    # Participation section
    writer.writerow(["staff_id", "assigned", "rate"])
    participation = report.get("participation", {}) or {}
    for staff_id, stats in sorted(participation.items()):
        rate_value = float(stats.get("rate", 0.0))
        writer.writerow([
            staff_id,
            stats.get("assigned", 0),
            f"{rate_value:.4f}"
        ])
    return output.getvalue()


__all__ = [
    "filter_shifts",
    "shifts_with_fill_status",
    "participation_rate_by_staff",
    "generate_report",
    "report_to_csv",
]
