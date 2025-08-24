from __future__ import annotations

from ..core.models import Status


_STATUS_COLORS = {
    Status.COMPLETED: ("#16a34a", "#16a34a"),  # green
    Status.ERROR: ("#dc2626", "#dc2626"),      # red
    Status.PAUSED: ("#eab308", "#eab308"),     # yellow
    Status.CANCELED: ("#52525b", "#52525b"),   # gray
    Status.DOWNLOADING: ("#3b82f6", "#3b82f6"),# blue
    Status.QUEUED: ("#a1a1aa", "#a1a1aa"),     # default
}


def status_color(status: Status | str):
    """Return a text color for a given download status."""
    if isinstance(status, str):
        try:
            status = Status(status)
        except ValueError:
            return _STATUS_COLORS[Status.QUEUED]
    return _STATUS_COLORS.get(status, _STATUS_COLORS[Status.QUEUED])

