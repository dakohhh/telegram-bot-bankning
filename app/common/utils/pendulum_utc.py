import pendulum
from datetime import datetime

def utc_now() -> datetime:
    """
    Helper function to get current UTC time using Pendulum.
    Returns a timezone-naive datetime object that's compatible with SQLAlchemy and PostgreSQL.
    """
    dt = pendulum.now("UTC")
    # Convert to standard datetime and remove timezone info
    return datetime(dt.year, dt.month, dt.day, dt.hour, dt.minute, dt.second, dt.microsecond)