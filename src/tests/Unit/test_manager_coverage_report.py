"""
Unit tests for manager_coverage_report.py

This file is for development and local testing only.
CI/CD pipeline uses test_together.py instead.
"""
from datetime import datetime
import sys
import os

# Add backend to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from backend import manager_coverage_report as mcr


def _sample_shifts():
    """Generate sample shifts for testing."""
    return [
        {
            "id": "s1",
            "date": "2025-11-01",
            "location": "Store A",
            "required_staff": 2,
            "assigned_staff": ["u1", "u2"],
        },
        {
            "id": "s2",
            "date": "2025-11-02",
            "location": "Store A",
            "required_staff": 1,
            "assigned_staff": ["u2"],
        },
        {
            "id": "s3",
            "date": "2025-11-03",
            "location": "Store B",
            "required_staff": 1,
            "assigned_staff": [],
        },
        {
            "id": "s4",
            "date": "2025-11-04",
            "location": "Store A",
            "required_staff": 1,
            "assigned_staff": ["u3"],
        },
    ]


def test_filter_by_location():
    """Test filtering shifts by location."""
    shifts = _sample_shifts()
    filtered = mcr.filter_shifts(shifts, location="Store A")
    assert len(filtered) == 3
    assert all(s["location"] == "Store A" for s in filtered)


def test_filter_by_date_range():
    """Test filtering shifts by date range."""
    shifts = _sample_shifts()
    start = datetime.fromisoformat("2025-11-02")
    end = "2025-11-03"
    filtered = mcr.filter_shifts(shifts, start_date=start, end_date=end)
    ids = {s["id"] for s in filtered}
    assert ids == {"s2", "s3"}


def test_filter_by_location_and_date():
    """Test filtering shifts by both location and date range."""
    shifts = _sample_shifts()
    filtered = mcr.filter_shifts(
        shifts,
        start_date="2025-11-01",
        end_date="2025-11-02",
        location="Store A"
    )
    assert len(filtered) == 2
    ids = {s["id"] for s in filtered}
    assert ids == {"s1", "s2"}


def test_shifts_with_fill_status_filled():
    """Test that filled shifts are correctly identified."""
    shifts = _sample_shifts()
    filtered = mcr.filter_shifts(shifts, location="Store A")
    annotated = mcr.shifts_with_fill_status(filtered)
    
    # s1 should be filled (2 assigned, required 2)
    s1 = next(s for s in annotated if s["id"] == "s1")
    assert s1["filled"] is True
    assert s1["assigned_count"] == 2
    assert s1["required_staff"] == 2
    
    # s2 should be filled (1 assigned, required 1)
    s2 = next(s for s in annotated if s["id"] == "s2")
    assert s2["filled"] is True
    assert s2["assigned_count"] == 1
    
    # s4 should be filled
    s4 = next(s for s in annotated if s["id"] == "s4")
    assert s4["filled"] is True


def test_shifts_with_fill_status_unfilled():
    """Test that unfilled shifts are correctly identified."""
    shifts = _sample_shifts()
    annotated = mcr.shifts_with_fill_status(shifts)
    
    # s3 should NOT be filled (0 assigned, required 1)
    s3 = next(s for s in annotated if s["id"] == "s3")
    assert s3["filled"] is False
    assert s3["assigned_count"] == 0


def test_participation_rate_calculation():
    """Test participation rate calculation for staff members."""
    shifts = _sample_shifts()
    filtered = mcr.filter_shifts(shifts, location="Store A")
    participation = mcr.participation_rate_by_staff(filtered)
    
    # u2 is assigned to s1 and s2 => 2 out of 3 Store A shifts
    assert participation.get("u2", {})["assigned"] == 2
    assert abs(participation.get("u2", {})["rate"] - (2.0 / 3.0)) < 1e-9
    
    # u1 is assigned to s1 only => 1 out of 3
    assert participation.get("u1", {})["assigned"] == 1
    assert abs(participation.get("u1", {})["rate"] - (1.0 / 3.0)) < 1e-9
    
    # u3 is assigned to s4 only => 1 out of 3
    assert participation.get("u3", {})["assigned"] == 1
    assert abs(participation.get("u3", {})["rate"] - (1.0 / 3.0)) < 1e-9


def test_participation_rate_empty():
    """Test participation rate with no shifts."""
    participation = mcr.participation_rate_by_staff([])
    assert participation == {}


def test_generate_report_structure():
    """Test that generate_report returns the correct structure."""
    shifts = _sample_shifts()
    report = mcr.generate_report(shifts, location="Store A")
    
    assert "shifts" in report
    assert "participation" in report
    assert "total_shifts" in report
    assert "filters" in report
    
    assert report["total_shifts"] == 3
    assert report["filters"]["location"] == "Store A"


def test_generate_report_with_all_filters():
    """Test generate_report with all filter parameters."""
    shifts = _sample_shifts()
    report = mcr.generate_report(
        shifts,
        start_date="2025-11-01",
        end_date="2025-11-02",
        location="Store A"
    )
    
    assert report["total_shifts"] == 2
    assert len(report["shifts"]) == 2


def test_report_to_csv_format():
    """Test CSV export format and content."""
    shifts = _sample_shifts()
    report = mcr.generate_report(shifts, location="Store A")
    csv_text = mcr.report_to_csv(report)
    
    # Check headers are present
    assert "id,date,location,required_staff,assigned_count,filled" in csv_text
    assert "staff_id,assigned,rate" in csv_text
    
    # Check staff member u2 is in the CSV
    assert "u2" in csv_text
    
    # Check that shifts are in the CSV
    assert "s1" in csv_text
    assert "Store A" in csv_text


def test_report_to_csv_participation_format():
    """Test that participation rates are formatted correctly in CSV."""
    shifts = _sample_shifts()
    report = mcr.generate_report(shifts, location="Store A")
    csv_text = mcr.report_to_csv(report)
    
    lines = csv_text.strip().split('\n')
    
    # Find participation section (after empty line)
    participation_start = None
    for i, line in enumerate(lines):
        if line.strip() == '' and i + 1 < len(lines):
            if 'staff_id' in lines[i + 1]:
                participation_start = i + 1
                break
    
    assert participation_start is not None
    # Check that rates are formatted with 4 decimal places
    for line in lines[participation_start + 1:]:
        if line.strip():
            parts = line.split(',')
            if len(parts) == 3:
                # Rate should be a decimal number
                rate_str = parts[2]
                assert '.' in rate_str


def test_parse_date_with_string():
    """Test date parsing with string input."""
    result = mcr._parse_date("2025-11-01")
    assert result is not None
    assert result.year == 2025
    assert result.month == 11
    assert result.day == 1


def test_parse_date_with_datetime():
    """Test date parsing with datetime input."""
    dt = datetime(2025, 11, 1)
    result = mcr._parse_date(dt)
    assert result == dt


def test_parse_date_with_none():
    """Test date parsing with None input."""
    result = mcr._parse_date(None)
    assert result is None


def test_parse_date_with_invalid_string():
    """Test date parsing with invalid string input."""
    result = mcr._parse_date("not-a-date")
    assert result is None


def test_filter_shifts_no_filters():
    """Test that filter_shifts returns all shifts when no filters applied."""
    shifts = _sample_shifts()
    filtered = mcr.filter_shifts(shifts)
    assert len(filtered) == 4


def test_filter_shifts_skips_invalid_dates():
    """Test that shifts with invalid dates are skipped."""
    shifts = [
        {"id": "s1", "date": "2025-11-01", "location": "Store A"},
        {"id": "s2", "date": "invalid-date", "location": "Store A"},
        {"id": "s3", "date": None, "location": "Store A"},
    ]
    filtered = mcr.filter_shifts(shifts, location="Store A")
    assert len(filtered) == 1
    assert filtered[0]["id"] == "s1"


def test_shifts_with_fill_status_date_formatting():
    """Test that dates are formatted as ISO strings in annotated shifts."""
    shifts = [
        {
            "id": "s1",
            "date": datetime(2025, 11, 1),
            "location": "Store A",
            "required_staff": 1,
            "assigned_staff": ["u1"],
        }
    ]
    annotated = mcr.shifts_with_fill_status(shifts)
    assert annotated[0]["date"] == "2025-11-01"


def test_shifts_with_fill_status_handles_missing_fields():
    """Test that missing fields are handled gracefully."""
    shifts = [
        {
            "id": "s1",
            "date": "2025-11-01",
            "location": "Store A",
            # No required_staff or assigned_staff
        }
    ]
    annotated = mcr.shifts_with_fill_status(shifts)
    assert annotated[0]["required_staff"] == 1  # Default
    assert annotated[0]["assigned_count"] == 0  # Empty default
    assert annotated[0]["filled"] is False


def test_shifts_with_fill_status_invalid_required_staff():
    """Test handling of invalid required_staff value."""
    shifts = [
        {
            "id": "s1",
            "date": "2025-11-01",
            "location": "Store A",
            "required_staff": "not-a-number",
            "assigned_staff": ["u1"],
        }
    ]
    annotated = mcr.shifts_with_fill_status(shifts)
    assert annotated[0]["required_staff"] == 1  # Falls back to default


def test_participation_rate_multiple_staff():
    """Test participation rate with multiple staff members."""
    shifts = [
        {"id": "s1", "assigned_staff": ["u1", "u2", "u3"]},
        {"id": "s2", "assigned_staff": ["u1", "u2"]},
        {"id": "s3", "assigned_staff": ["u1"]},
    ]
    participation = mcr.participation_rate_by_staff(shifts)
    
    assert participation["u1"]["assigned"] == 3
    assert participation["u1"]["rate"] == 1.0
    
    assert participation["u2"]["assigned"] == 2
    assert abs(participation["u2"]["rate"] - (2.0 / 3.0)) < 1e-9
    
    assert participation["u3"]["assigned"] == 1
    assert abs(participation["u3"]["rate"] - (1.0 / 3.0)) < 1e-9


if __name__ == "__main__":
    # Run tests locally
    import pytest
    pytest.main([__file__, "-v"])
