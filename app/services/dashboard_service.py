from datetime import datetime, timezone
from typing import Any

from app.services import campaign_service
from app.services.live_cache_service import get_all_live_snapshots, get_live_snapshot


def _to_live_response(snapshot: dict[str, Any], campaign: dict[str, Any] | None = None) -> dict[str, Any]:
    connected = int(snapshot["connected"])
    not_connected = int(snapshot["not_connected"])
    total_uploads = int(snapshot["total_uploads"])
    percentage = round((connected / total_uploads * 100) if total_uploads > 0 else 0.0, 2)

    if campaign:
        status = campaign_service.get_runtime_status_label(campaign)
    else:
        status = "COMPLETED"

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
