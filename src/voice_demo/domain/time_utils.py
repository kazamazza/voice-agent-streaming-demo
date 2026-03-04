from datetime import datetime, timezone


def utcnow() -> datetime:
    """
    Returns timezone-aware UTC timestamp.
    Centralized helper so we avoid datetime.utcnow() and
    can mock in tests if needed.
    """
    return datetime.now(timezone.utc)


def utcnow_iso() -> str:
    # stable + readable for metadata
    return utcnow().isoformat().replace("+00:00", "Z")
