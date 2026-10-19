"""Utilidades de tiempo: reloj UTC en segundos Unix y formato ISO 8601."""

import time
from datetime import datetime, timezone


def ahora():
    return time.time()


def iso(ts):
    if ts is None:
        return None
    return datetime.fromtimestamp(ts, tz=timezone.utc).isoformat()
