from datetime import datetime, timezone
from typing import Any
from zoneinfo import ZoneInfo

from fastapi import HTTPException

from app.core.config import get_settings
from app.core.storage import (
    campaign_timeseries_exists,
    get_campaign as storage_get_campaign,
    list_campaigns as storage_list_campaigns,
    save_campaign,
)
from app.models.campaign import CampaignStatus
from app.schemas.campaign import CampaignCreate, CampaignUpdate

DEFAULT_CONFIG = {
    "connected_ratio": 0.6,
    "not_connected_ratio": 0.25,
    "pending_ratio": 0.15,
    "curve_type": "sigmoid",
    "noise_level": 0.02,
    "interval_seconds": 5,
}

_settings = get_settings()
try:
    _default_tz = ZoneInfo(getattr(_settings, "DEFAULT_TIMEZONE", "UTC"))
except Exception:
    _default_tz = timezone.utc


def _as_utc(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=_default_tz)
    return dt.astimezone(timezone.utc)


def _serialize_dt(dt: datetime) -> str:
    return _as_utc(dt).isoformat()


def _parse_iso_dt(raw: str) -> datetime:
    dt = datetime.fromisoformat(raw)
    return _as_utc(dt)


def _campaign_dt(campaign: dict[str, Any], key: str) -> datetime | None:
    value = campaign.get(key)
    if isinstance(value, datetime):
        return _as_utc(value)
    if isinstance(value, str) and value:
        return _parse_iso_dt(value)
    return None


def _normalized_config(raw: dict[str, Any] | None) -> dict[str, Any]:
    merged = DEFAULT_CONFIG | (raw or {})
    return {
        "connected_ratio": float(merged["connected_ratio"]),
        "not_connected_ratio": float(merged["not_connected_ratio"]),
        "pending_ratio": float(merged["pending_ratio"]),
        "curve_type": str(merged["curve_type"]),
        "noise_level": float(merged["noise_level"]),
        "interval_seconds": int(merged["interval_seconds"]),
    }


def _ensure_campaign(campaign_id: str | int) -> dict[str, Any]:
    campaign = storage_get_campaign(campaign_id)
    if not campaign:
        raise HTTPException(status_code=404, detail=f"Campaign {campaign_id} not found")
    return campaign


def get_runtime_status_label(campaign: dict[str, Any]) -> str:
    """Compute campaign status from current time and campaign window."""
    now = datetime.now(timezone.utc)
    start = _campaign_dt(campaign, "start_time")
    end = _campaign_dt(campaign, "end_time")

    if start and end:
        if now >= end:
            return "COMPLETED"
        if now >= start:
            return "IN_PROGRESS"

    return str(campaign.get("status") or CampaignStatus.PLANNED.value)


def campaign_to_response(campaign: dict[str, Any]) -> dict[str, Any]:
    campaign_id = str(campaign.get("id", ""))
    config = _normalized_config(campaign.get("config") if isinstance(campaign.get("config"), dict) else None)

    return {
        "id": campaign_id,
        "name": str(campaign.get("name", "")),
        "start_time": campaign.get("start_time"),
        "end_time": campaign.get("end_time"),
        "target_total": int(campaign.get("target_total", 0)),
        "status": get_runtime_status_label(campaign),
        "config": {
            "id": campaign_id,
            "campaign_id": campaign_id,
            **config,
        },
    }


def create_campaign(data: CampaignCreate) -> dict[str, Any]:
    """Create a new campaign with file storage backend."""
    campaign_id = data.campaign_id.strip()
    if storage_get_campaign(campaign_id):
        raise HTTPException(status_code=409, detail=f"Campaign {campaign_id} already exists")

    campaign = {
        "id": campaign_id,
        "name": data.name,
        "start_time": _serialize_dt(data.start_time),
        "end_time": _serialize_dt(data.end_time),
        "target_total": int(data.target_total),
        "status": CampaignStatus.PLANNED.value,
        "config": _normalized_config(data.config.model_dump()),
    }
    save_campaign(campaign)
    return campaign


def get_campaign(campaign_id: str | int) -> dict[str, Any]:
    return _ensure_campaign(campaign_id)


def get_campaign_with_config(campaign_id: str | int) -> dict[str, Any]:
    campaign = _ensure_campaign(campaign_id)
    return {"campaign": campaign, "config": campaign.get("config", {})}


def list_campaigns() -> list[dict[str, Any]]:
    """Return all campaigns ordered by id descending."""
    return storage_list_campaigns()


def update_campaign_status(campaign_id: str | int, status: CampaignStatus) -> dict[str, Any]:
    campaign = _ensure_campaign(campaign_id)
    campaign["status"] = status.value
    save_campaign(campaign)
    return campaign


def update_campaign(campaign_id: str | int, data: CampaignUpdate) -> dict[str, Any]:
    """Update campaign + config before simulation is generated."""
    campaign = _ensure_campaign(campaign_id)

    if campaign_timeseries_exists(campaign_id):
        raise HTTPException(
            status_code=400,
            detail=(
                f"Campaign {campaign_id} already has generated simulation data. "
                "Modification is allowed only before generation."
            ),
        )

    campaign["name"] = data.name
    campaign["start_time"] = _serialize_dt(data.start_time)
    campaign["end_time"] = _serialize_dt(data.end_time)
    campaign["target_total"] = int(data.target_total)
    campaign["config"] = _normalized_config(data.config.model_dump())
    campaign["status"] = CampaignStatus.PLANNED.value

    save_campaign(campaign)
    return campaign
