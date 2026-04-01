from collections import deque
from datetime import datetime, timezone
from threading import RLock
from typing import Deque

from app.core.storage import latest_timeseries_window
from app.services import campaign_service

_CACHE_LIMIT = 10
_cache_lock = RLock()
_cache: dict[str, Deque[dict[str, object]]] = {}
_last_refresh: datetime | None = None


def _build_snapshot(
    campaign_id: str,
    timestamp: datetime,
    connected: int,
    not_connected: int,
) -> dict[str, object]:
    total_uploads = connected + not_connected
    return {
        "campaign_id": campaign_id,
        "timestamp": timestamp,
        "total_uploads": total_uploads,
        "connected": connected,
        "not_connected": not_connected,
    }


def _row_to_snapshot(campaign_id: str, row: dict[str, object]) -> dict[str, object]:
    connected = int(row.get("connected", 0))
    not_connected = int(row.get("notconnected", 0))
    timestamp = row.get("time")
    if not isinstance(timestamp, datetime):
        timestamp = datetime.now(timezone.utc)
    return _build_snapshot(campaign_id, timestamp, connected, not_connected)


def _select_latest_snapshot(
    rows: Deque[dict[str, object]],
    at_time: datetime,
) -> dict[str, object] | None:
    latest: dict[str, object] | None = None
    for row in rows:
        timestamp = row.get("timestamp")
        if not isinstance(timestamp, datetime):
            continue
        if timestamp <= at_time:
            latest = row
        else:
            break
    return latest


def refresh_live_cache(now: datetime | None = None) -> None:
    global _last_refresh

    if now is None:
        now = datetime.now(timezone.utc)

    campaigns = campaign_service.list_campaigns()

    with _cache_lock:
        for campaign in campaigns:
            campaign_id = str(campaign["id"])
            rows = latest_timeseries_window(campaign_id, now, _CACHE_LIMIT)
            if rows:
                snapshots = [_row_to_snapshot(campaign_id, row) for row in rows]
            else:
                snapshots = [_build_snapshot(campaign_id, now, 0, 0)]
            _cache[campaign_id] = deque(snapshots, maxlen=_CACHE_LIMIT)
        _last_refresh = now


def get_live_snapshot(campaign_id: str) -> dict[str, object]:
    now = datetime.now(timezone.utc)

    with _cache_lock:
        rows = _cache.get(campaign_id)
        if rows:
            latest = _select_latest_snapshot(rows, now)
            if latest:
                return latest

    rows = latest_timeseries_window(campaign_id, now, 1)
    if rows:
        return _row_to_snapshot(campaign_id, rows[-1])

    return _build_snapshot(campaign_id, now, 0, 0)


def get_all_live_snapshots() -> list[dict[str, object]]:
    campaigns = campaign_service.list_campaigns()
    now = datetime.now(timezone.utc)

    snapshots: list[dict[str, object] | None] = [None] * len(campaigns)
    missing: list[tuple[int, str]] = []

    with _cache_lock:
        for idx, campaign in enumerate(campaigns):
            campaign_id = str(campaign["id"])
            rows = _cache.get(campaign_id)
            if rows:
                latest = _select_latest_snapshot(rows, now)
                if latest:
                    snapshots[idx] = latest
                else:
                    missing.append((idx, campaign_id))
            else:
                missing.append((idx, campaign_id))

    for idx, campaign_id in missing:
        rows = latest_timeseries_window(campaign_id, now, 1)
        if rows:
            snapshots[idx] = _row_to_snapshot(campaign_id, rows[-1])
        else:
            snapshots[idx] = _build_snapshot(campaign_id, now, 0, 0)

    return [item for item in snapshots if item is not None]


def get_live_history(campaign_id: str) -> list[dict[str, object]]:
    with _cache_lock:
        rows = _cache.get(campaign_id)
        if rows:
            return list(rows)

    return []
