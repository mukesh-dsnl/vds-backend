from datetime import datetime, timezone
from typing import Any

from app.services import campaign_service
from app.services.live_cache_service import get_all_live_snapshots, get_live_snapshot


def _to_live_response(snapshot: dict[str, Any]) -> dict[str, Any]:
    return {
        "campaign_id": str(snapshot["campaign_id"]),
        "timestamp": snapshot["timestamp"],
        "total_uploads": int(snapshot["total_uploads"]),
        "connected": int(snapshot["connected"]),
        "not_connected": int(snapshot["not_connected"]),
    }


def get_live_stats(campaign_id: str | int) -> dict[str, Any]:
    campaign = campaign_service.get_campaign(campaign_id)
    snapshot = get_live_snapshot(str(campaign["id"]))
    return _to_live_response(snapshot)


def get_all_live_stats() -> list[dict[str, Any]]:
    campaigns = campaign_service.list_campaigns()
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
        results.append(_to_live_response(snapshot))

    return results
