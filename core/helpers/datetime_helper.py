from datetime import datetime, timedelta


def get_current_date_context_helper():
    """
    Generate current date context
    inputs: None
    outputs: dict with current date information
    { "current_date_str": "September 14, 2023", "current_date_iso": "2023-09-14",
    "last_week_start": "2023-09-04", "last_week_end": "2023-09-10",
    "current_month": "September 2023", "current_year": 2023,
    "last_month": "August 2023", "last_month_iso": "2023-08" }
    """

    current_date = datetime.now()
    current_date_str = current_date.strftime("%B %d, %Y")
    current_date_iso = current_date.strftime("%Y-%m-%d")

    days_since_monday = current_date.weekday()
    last_week_start = current_date - timedelta(days=days_since_monday + 7)
    last_week_end = last_week_start + timedelta(days=6)
    last_month = current_date - timedelta(days=current_date.day)

    return {
        "current_date_str": current_date_str,
        "current_date_iso": current_date_iso,
        "last_week_start": last_week_start.strftime("%Y-%m-%d"),
        "last_week_end": last_week_end.strftime("%Y-%m-%d"),
        "current_month": current_date.strftime("%B %Y"),
        "current_year": current_date.year,
        "last_month": last_month.strftime("%B %Y"),
        "last_month_iso": last_month.strftime("%Y-%m"),
    }


def current_day_formatted() -> str:
    """Returns the current day formatted as 'YYYY-MM-DD'"""
    return datetime.now().strftime("%Y-%m-%d")
