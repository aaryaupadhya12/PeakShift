"""Manager coverage reporting API endpoints."""

from typing import Optional
from fastapi import APIRouter, HTTPException, Response
from pydantic import BaseModel
from backend.config import get_connection
from backend import manager_coverage_report as mcr

router = APIRouter()


class CoverageReportRequest(BaseModel):
    """Request model for coverage report generation."""
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    location: Optional[str] = None


@router.post("/reports/coverage")
async def generate_coverage_report(request: CoverageReportRequest):
    """
    Generate a coverage report for managers.

    Shows shift fill status and participation rates.
    Can be filtered by date range and location.
    """
    try:
        conn = get_connection()
        cursor = conn.cursor()

        # Fetch all shifts with assigned staff information
        shifts_query = """
            SELECT
                s.id,
                s.title,
                s.date,
                s.start_time,
                s.end_time,
                s.spots as required_staff,
                s.location,
                s.created_by
            FROM shifts s
            WHERE s.status = 'published'
        """

        shifts_data = cursor.execute(shifts_query).fetchall()

        # Convert to list of dicts and add assigned_staff
        shifts = []
        for shift in shifts_data:
            shift_dict = dict(shift)

            # Get assigned staff for this shift
            assigned = cursor.execute("""
                SELECT username
                FROM volunteer_commitments
                WHERE shift_id = ? AND status = 'approved'
            """, (shift['id'],)).fetchall()

            shift_dict['assigned_staff'] = [row['username'] for row in assigned]
            shifts.append(shift_dict)

        conn.close()

        # Generate report using the manager_coverage_report module
        report = mcr.generate_report(
            shifts,
            start_date=request.start_date,
            end_date=request.end_date,
            location=request.location
        )

        return report

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to generate report: {str(e)}"
        ) from e


@router.post("/reports/coverage/export")
async def export_coverage_report(request: CoverageReportRequest):
    """
    Export coverage report to CSV format.

    Returns a CSV file with shift fill status and participation rates.
    """
    try:
        conn = get_connection()
        cursor = conn.cursor()

        # Fetch all shifts with assigned staff information (same as above)
        shifts_query = """
            SELECT
                s.id,
                s.title,
                s.date,
                s.start_time,
                s.end_time,
                s.spots as required_staff,
                s.location,
                s.created_by
            FROM shifts s
            WHERE s.status = 'published'
        """

        shifts_data = cursor.execute(shifts_query).fetchall()

        # Convert to list of dicts and add assigned_staff
        shifts = []
        for shift in shifts_data:
            shift_dict = dict(shift)

            # Get assigned staff for this shift
            assigned = cursor.execute("""
                SELECT username
                FROM volunteer_commitments
                WHERE shift_id = ? AND status = 'approved'
            """, (shift['id'],)).fetchall()

            shift_dict['assigned_staff'] = [row['username'] for row in assigned]
            shifts.append(shift_dict)

        conn.close()

        # Generate report
        report = mcr.generate_report(
            shifts,
            start_date=request.start_date,
            end_date=request.end_date,
            location=request.location
        )

        # Convert to CSV
        csv_content = mcr.report_to_csv(report)

        # Return as downloadable CSV file
        return Response(
            content=csv_content,
            media_type="text/csv",
            headers={
                "Content-Disposition": "attachment; filename=coverage_report.csv"
            }
        )

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to export report: {str(e)}"
        ) from e
