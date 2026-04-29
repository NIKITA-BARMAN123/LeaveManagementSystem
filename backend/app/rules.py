from datetime import date

def compute_days(start: date, end: date) -> int:
    return (end - start).days + 1

def validate_dates(start: date, end: date) -> str | None:
    if start > end:
        return "Start date cannot be after end date."
    return None