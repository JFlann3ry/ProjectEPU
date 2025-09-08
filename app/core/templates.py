from datetime import date, datetime

from fastapi.templating import Jinja2Templates


def _datefmt(value, fmt: str = "%d-%m-%Y") -> str:
    """
    Jinja filter: Format a date/datetime using DD-MM-YYYY by default.
    - If value has strftime, use it.
    - If value is a string, return as-is (avoid guessing formats).
    - On None or error, return empty string.
    """
    try:
        if value is None:
            return ""
        if hasattr(value, "strftime"):
            return value.strftime(fmt)
        # Avoid parsing arbitrary strings; just return string
        return str(value)
    except Exception:
        return ""


templates = Jinja2Templates(directory="templates")
templates.env.filters["datefmt"] = _datefmt
# Expose a callable that returns a datetime object so templates can use .strftime('%Y') etc.
templates.env.globals["now"] = lambda: datetime.now()


def _dtfmt(value, fmt: str = "%d-%m-%Y %H:%M") -> str:
    """Format a datetime with time; falls back to datefmt if not datetime-like."""
    return _datefmt(value, fmt)


def _relativetime(value) -> str:
    """
    Human-friendly relative time, e.g., "just now", "5 minutes ago", "2 days ago", "in 3 hours".
    Accepts datetime or date. Naive datetimes are assumed local now().
    """
    try:
        if value is None:
            return ""
        now = (
            datetime.now(tz=value.tzinfo)
            if isinstance(value, datetime) and value.tzinfo
            else datetime.now()
        )
        if isinstance(value, date) and not isinstance(value, datetime):
            value_dt = datetime(value.year, value.month, value.day)
        else:
            value_dt = value if isinstance(value, datetime) else datetime.fromisoformat(str(value))
        delta = value_dt - now
        seconds = int(delta.total_seconds())
        future = seconds > 0
        seconds = abs(seconds)

        def unit(n, w):
            return f"{n} {w}{'' if n == 1 else 's'}"

        if seconds < 10:
            return "just now" if not future else "in a few seconds"
        mins = seconds // 60
        if mins < 1:
            return unit(seconds, "second") + (" ago" if not future else " from now")
        hrs = mins // 60
        if hrs < 1:
            return unit(mins, "minute") + (" ago" if not future else " from now")
        days = hrs // 24
        if days < 1:
            return unit(hrs, "hour") + (" ago" if not future else " from now")
        if days < 30:
            return unit(days, "day") + (" ago" if not future else " from now")
        months = days // 30
        if months < 12:
            return unit(months, "month") + (" ago" if not future else " from now")
        years = months // 12
        return unit(years, "year") + (" ago" if not future else " from now")
    except Exception:
        return ""


templates.env.filters["dtfmt"] = _dtfmt
templates.env.filters["relativetime"] = _relativetime


def _ordsuffix(value) -> str:
    """Return the English ordinal suffix for a given day or integer: 1->'st', 2->'nd', ..."""
    try:
        if value is None:
            return ""
        # Extract numeric value from date/datetime or int-like
        if hasattr(value, "day"):
            n = int(value.day)
        else:
            n = int(value)
        if 11 <= (n % 100) <= 13:
            return "th"
        return {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")
    except Exception:
        return ""


templates.env.filters["ordsuffix"] = _ordsuffix
