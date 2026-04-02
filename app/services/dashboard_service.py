from datetime import datetime, timezone
from typing import Any

from app.services import campaign_service
from app.services.live_cache_service import get_all_live_snapshots, get_live_snapshot


def get_consolidate_stats() -> dict[str, Any]:
    """
    Compute and persist consolidated campaign counts.
    Status is determined at runtime for every campaign.
    """
    from app.core.storage import save_consolidate

    all_campaigns = campaign_service.list_campaigns()
    planned = sum(
        1 for c in all_campaigns
        if campaign_service.get_runtime_status_label(c) == "PLANNED"
    )
    in_progress = sum(
        1 for c in all_campaigns
        if campaign_service.get_runtime_status_label(c) == "IN_PROGRESS"
    )
    completed = sum(
        1 for c in all_campaigns
        if campaign_service.get_runtime_status_label(c) == "COMPLETED"
    )
    total = len(all_campaigns)
    return save_consolidate(total, planned, in_progress, completed)


def _to_live_response(snapshot: dict[str, Any], campaign: dict[str, Any] | None = None) -> dict[str, Any]:
    connected = int(snapshot["connected"])
    not_connected = int(snapshot["not_connected"])

    # total_uploads is the campaign's target_total, not the running sum of the snapshot
    if campaign:
        total_uploads = int(campaign.get("target_total") or 0)
        status = campaign_service.get_runtime_status_label(campaign)
    else:
        total_uploads = int(snapshot.get("total_uploads", connected + not_connected))
        status = "COMPLETED"

    # percentage = overall progress (how many processed out of total target)
    current_total = connected + not_connected
    percentage = round((current_total / total_uploads * 100) if total_uploads > 0 else 0.0, 2)

    return {
        "campaign_id": str(snapshot["campaign_id"]),
        "timestamp": snapshot["timestamp"],
        "total_uploads": total_uploads,
        "connected": connected,
        "not_connected": not_connected,
        "percentage": percentage,
        "status": status,
    }


def get_live_stats(campaign_id: str | int) -> dict[str, Any]:
    campaign = campaign_service.get_campaign(campaign_id)
    snapshot = get_live_snapshot(str(campaign["id"]))
    return _to_live_response(snapshot, campaign)


def get_all_live_stats() -> list[dict[str, Any]]:
    campaigns = campaign_service.list_campaigns()
    campaign_map = {str(c["id"]): c for c in campaigns}
    snapshots = {
        str(item["campaign_id"]): item
        for item in get_all_live_snapshots()
    }
    now = datetime.now(timezone.utc)

    results: list[dict[str, Any]] = []
    for campaign in campaigns:
        campaign_id = str(campaign["id"])
        snapshot = snapshots.get(campaign_id)
        if not snapshot:
            snapshot = {
                "campaign_id": campaign_id,
                "timestamp": now,
                "total_uploads": 0,
                "connected": 0,
                "not_connected": 0,
            }
        results.append(_to_live_response(snapshot, campaign_map.get(campaign_id)))

    return results


def get_live_only_stats() -> list[dict[str, Any]]:
    """Return live snapshot for campaigns that are PLANNED or IN_PROGRESS."""
    active_campaigns = campaign_service.list_active_campaigns()
    if not active_campaigns:
        return []

    # Keep only campaigns whose runtime status is PLANNED or IN_PROGRESS
    live_campaigns = [
        c for c in active_campaigns
        if campaign_service.get_runtime_status_label(c) in ("PLANNED", "IN_PROGRESS")
    ]
    if not live_campaigns:
        return []

    campaign_map = {str(c["id"]): c for c in live_campaigns}
    snapshots = {
        str(item["campaign_id"]): item
        for item in get_all_live_snapshots()
        if is_campaign_active(str(item["campaign_id"]))
    }
    now = datetime.now(timezone.utc)

    results: list[dict[str, Any]] = []
    for campaign in live_campaigns:
        campaign_id = str(campaign["id"])
        snapshot = snapshots.get(campaign_id) or {
            "campaign_id": campaign_id,
            "timestamp": now,
            "total_uploads": 0,
            "connected": 0,
            "not_connected": 0,
        }
        results.append(_to_live_response(snapshot, campaign_map.get(campaign_id)))

    return results


def get_archived_stats(date_filter: str | None = None) -> list[dict[str, Any]]:
    """
    Return the final snapshot for each archived campaign from campaigns.json.

    Args:
        date_filter: Optional ``YYYY-MM-DD`` string to filter by start_time date in IST.
    """
    entries = campaign_service.list_completed_campaigns(date_filter)
    results: list[dict[str, Any]] = []

    for entry in entries:
        campaign_id = str(entry.get("id", ""))
        snap = entry.get("snapshot") or {}

        ts = snap.get("timestamp") or entry.get("end_time", "")
        if isinstance(ts, str):
            try:
                from datetime import datetime as _dt
                ts = _dt.fromisoformat(ts)
            except ValueError:
                ts = datetime.now(timezone.utc)

        target_total = int(entry.get("target_total", 0))
        connected = int(snap.get("connected", 0))
        not_connected = int(snap.get("not_connected", 0))
        current_total = connected + not_connected
        percentage = round((current_total / target_total * 100) if target_total > 0 else 0.0, 2)

        results.append({
            "campaign_id": campaign_id,
            "name": str(entry.get("name", "")),
            "start_time": entry.get("start_time"),
            "end_time": entry.get("end_time"),
            "target_total": target_total,
            "timestamp": ts,
            "total_uploads": target_total,
            "connected": connected,
            "not_connected": not_connected,
            "percentage": percentage,
            "status": "COMPLETED",
        })

    return results


def is_campaign_active(campaign_id: str) -> bool:
    from app.core.storage import is_campaign_active as _is_active
    return _is_active(campaign_id)

