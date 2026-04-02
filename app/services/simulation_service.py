import logging
from datetime import timedelta

from fastapi import HTTPException

from app.core.storage import campaign_timeseries_exists, save_campaign, write_timeseries_rows
from app.utils.curve import apply_curve
from app.utils.noise import apply_noise
from app.services import campaign_service

logger = logging.getLogger(__name__)


def generate_time_series(campaign_id: str) -> int:
    """
    Pre-generate time-series CSV data for a campaign.

    Algorithm:
        1. Iterate from start_time to end_time in interval_seconds steps.
        2. Compute curve-adjusted progress with optional noise.
        3. Build monotonically increasing total uploads.
        4. Split uploads into connected and notconnected counts.
        5. Persist rows to storage/campaigns/{campaign_id}/{campaign_id}.csv.

    Returns:
        Number of rows written.
    """

    campaign = campaign_service.get_campaign(campaign_id)

    if campaign_timeseries_exists(campaign_id):
        raise HTTPException(
            status_code=400,
            detail=(
                f"Campaign {campaign_id} already has a {campaign_id}.csv file. "
                "Replace it manually or via upload endpoint before regenerating."
            ),
        )

    start = campaign_service._parse_iso_dt(campaign["start_time"])
    end = campaign_service._parse_iso_dt(campaign["end_time"])
    total_duration = (end - start).total_seconds()
    if total_duration <= 0:
        raise HTTPException(status_code=400, detail="Campaign duration must be > 0")

    config = campaign_service.DEFAULT_CONFIG | campaign.get("config", {})

    interval = int(config.get("interval_seconds", 5))
    if interval <= 0:
        raise HTTPException(status_code=400, detail="interval_seconds must be > 0")

    target = int(campaign["target_total"])
    if target <= 0:
        raise HTTPException(status_code=400, detail="target_total must be > 0")

    connected_ratio = float(config.get("connected_ratio", 0.6))
    not_connected_ratio = float(config.get("not_connected_ratio", 0.25))
    ratio_sum = max(connected_ratio + not_connected_ratio, 0.0)
    if ratio_sum <= 0:
        connected_share = 1.0
        not_connected_share = 0.0
    else:
        connected_share = connected_ratio / ratio_sum
        not_connected_share = not_connected_ratio / ratio_sum
    curve_type = str(config.get("curve_type", "sigmoid"))
    noise_level = float(config.get("noise_level", 0.02))

    rows: list[dict] = []
    prev_total = 0
    elapsed = 0.0

    while elapsed <= total_duration:
        progress = elapsed / total_duration

        adjusted = apply_curve(progress, curve_type)
        adjusted = apply_noise(adjusted, noise_level)
        adjusted = max(0.0, min(1.0, adjusted))

        raw_total = int(round(target * adjusted))
        raw_total = max(prev_total, raw_total)
        raw_total = min(raw_total, target)

        connected = int(round(raw_total * connected_share))
        connected = max(0, min(connected, raw_total))
        not_connected = max(raw_total - connected, 0)

        current_ts = start + timedelta(seconds=elapsed)

        rows.append(
            {
                "time": current_ts,
                "connected": connected,
                "notconnected": not_connected,
            }
        )

        prev_total = raw_total
        elapsed += interval

    if rows:
        last = rows[-1]
        connected = max(0, min(int(round(target * connected_share)), target))
        last["connected"] = connected
        last["notconnected"] = max(target - connected, 0)

    write_timeseries_rows(campaign_id, rows)

    campaign["status"] = "READY"
    save_campaign(campaign)

    # Refresh consolidate counts now that a new campaign is ready
    try:
        from app.services.dashboard_service import get_consolidate_stats
        get_consolidate_stats()
    except Exception:
        pass

    logger.info(
        "Campaign %s: simulation complete — %d rows generated", campaign_id, len(rows)
    )
    return len(rows)
