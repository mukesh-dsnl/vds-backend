import csv
import io
import json
import re
import shutil
from collections import deque
from datetime import datetime, timedelta, timezone
from pathlib import Path
from threading import RLock
from typing import Any
from zoneinfo import ZoneInfo

from fastapi import HTTPException

from app.core.config import get_settings

CSV_HEADERS = ["time", "connected", "notconnected"]
LEGACY_CSV_HEADERS = ["time", "Completed", "Total"]
CSV_TIME_FORMAT = "%Y-%m-%d %H:%M:%S"
CAMPAIGN_ID_PATTERN = re.compile(r"^[A-Za-z0-9_-]{1,10}$")

_settings = get_settings()
try:
    _default_tz = ZoneInfo(getattr(_settings, "DEFAULT_TIMEZONE", "UTC"))
except Exception:
    _default_tz = timezone.utc
_IST = ZoneInfo("Asia/Kolkata")
_storage_root = Path(getattr(_settings, "STORAGE_DIR", "storage")).resolve()
_campaigns_root = _storage_root / "campaigns"
_past_campaigns_root = _storage_root / "past_campaigns"
_completed_campaigns_file = _storage_root / "campaigns.json"
_admin_file = _storage_root / "admin.json"
_clients_file = _storage_root / "clients.json"
_credits_file = _storage_root / "credits.json"
_consolidate_file = _storage_root / "consolidate.json"
_io_lock = RLock()


def _normalize_campaign_id(campaign_id: str | int) -> str:
    normalized = str(campaign_id).strip()
    if not normalized or not CAMPAIGN_ID_PATTERN.fullmatch(normalized):
        raise HTTPException(
            status_code=400,
            detail=(
                "Invalid campaign_id. Use only letters, numbers, underscore, and hyphen "
                "(max 10 chars)."
            ),
        )
    return normalized


def _read_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2)


def _serialize_dt(value: datetime) -> str:
    """Serialise a datetime as IST (+05:30) ISO-8601 string."""
    if value.tzinfo is None:
        value = value.replace(tzinfo=_default_tz)
    return value.astimezone(_IST).isoformat()


def _parse_iso_dt(raw: str) -> datetime:
    dt = datetime.fromisoformat(raw)
    if dt.tzinfo is None:
        return dt.replace(tzinfo=_default_tz).astimezone(timezone.utc)
    return dt.astimezone(timezone.utc)


def _campaign_meta_path(campaign_id: str | int) -> Path:
    normalized_id = _normalize_campaign_id(campaign_id)
    return _campaigns_root / normalized_id / f"{normalized_id}.json"


def _campaign_timeseries_path(campaign_id: str | int) -> Path:
    normalized_id = _normalize_campaign_id(campaign_id)
    return _campaigns_root / normalized_id / f"{normalized_id}.csv"


def _migrate_legacy_campaign_files() -> None:
    if not _campaigns_root.exists():
        return

    for item in _campaigns_root.iterdir():
        if not item.is_dir() or not CAMPAIGN_ID_PATTERN.fullmatch(item.name):
            continue

        campaign_id = item.name
        new_json = item / f"{campaign_id}.json"
        legacy_json = item / "campaign.json"

        if legacy_json.exists() and not new_json.exists():
            legacy_json.rename(new_json)

        new_csv = item / f"{campaign_id}.csv"
        legacy_csv = item / "timeseries.csv"

        if legacy_csv.exists() and not new_csv.exists():
            legacy_csv.rename(new_csv)


def _seed_test_campaign() -> None:
    if list_campaign_ids():
        return

    if _read_json(_completed_campaigns_file, {}):
        return

    now = datetime.now(timezone.utc)
    start = (now - timedelta(minutes=10)).replace(microsecond=0)
    end = (now + timedelta(minutes=50)).replace(microsecond=0)
    target_total = 1200
    sample_campaign_id = "sample-001"

    campaign = {
        "id": sample_campaign_id,
        "name": "Sample Campaign",
        "start_time": _serialize_dt(start),
        "end_time": _serialize_dt(end),
        "target_total": target_total,
        "status": "READY",
        "config": {
            "connected_ratio": 0.62,
            "not_connected_ratio": 0.23,
            "pending_ratio": 0.15,
            "curve_type": "sigmoid",
            "noise_level": 0.02,
            "interval_seconds": 60,
        },
    }
    save_campaign(campaign)

    rows: list[dict[str, Any]] = []
    steps = 12
    for idx in range(steps + 1):
        at = start + timedelta(minutes=idx * 5)
        total = min(target_total, int(round((target_total * idx) / steps)))
        connected = min(total, int(round(total * 0.62)))
        not_connected = max(total - connected, 0)
        rows.append({"time": at, "connected": connected, "notconnected": not_connected})

    write_timeseries_rows(sample_campaign_id, rows)


def ensure_storage_initialized() -> None:
    with _io_lock:
        _campaigns_root.mkdir(parents=True, exist_ok=True)
        _past_campaigns_root.mkdir(parents=True, exist_ok=True)
        _migrate_legacy_campaign_files()

        if not _admin_file.exists():
            _write_json(
                _admin_file,
                {
                    "admins": [
                        {
                            "username": "admin",
                            "password": "admin123",
                            "display_name": "System Admin",
                        }
                    ]
                },
            )

        if not _clients_file.exists():
            _write_json(
                _clients_file,
                {
                    "clients": [
                        {
                            "username": "client1",
                            "password": "client123",
                            "display_name": "Client One",
                        }
                    ]
                },
            )

        if not _credits_file.exists():
            _write_json(
                _credits_file,
                {"total_credits": 0, "used_credits": 0, "available_credits": 0},
            )

        if not _consolidate_file.exists():
            _write_json(
                _consolidate_file,
                {"total": 0, "planned": 0, "in_progress": 0, "completed": 0, "last_updated": None},
            )

        _seed_test_campaign()


def get_credits() -> dict[str, Any]:
    """Read credits from storage/credits.json."""
    data = _read_json(_credits_file, {"total_credits": 0, "used_credits": 0, "available_credits": 0})
    return {
        "total_credits": int(data.get("total_credits", 0)),
        "used_credits": int(data.get("used_credits", 0)),
        "available_credits": int(data.get("available_credits", 0)),
    }


def save_credits(total_credits: int, used_credits: int) -> dict[str, Any]:
    """Persist credits and recompute available_credits."""
    available = max(total_credits - used_credits, 0)
    payload = {
        "total_credits": total_credits,
        "used_credits": used_credits,
        "available_credits": available,
    }
    with _io_lock:
        _write_json(_credits_file, payload)
    return payload


def get_consolidate() -> dict[str, Any]:
    """Read consolidate stats from storage/consolidate.json."""
    default = {"total": 0, "planned": 0, "in_progress": 0, "completed": 0, "last_updated": None}
    return _read_json(_consolidate_file, default)


def save_consolidate(total: int, planned: int, in_progress: int, completed: int) -> dict[str, Any]:
    """Persist consolidate campaign counts."""
    payload = {
        "total": total,
        "planned": planned,
        "in_progress": in_progress,
        "completed": completed,
        "last_updated": _serialize_dt(datetime.now(timezone.utc)),
    }
    with _io_lock:
        _write_json(_consolidate_file, payload)
    return payload


def list_campaign_ids() -> list[str]:
    if not _campaigns_root.exists():
        return []

    ids: list[str] = []
    for item in _campaigns_root.iterdir():
        if item.is_dir() and CAMPAIGN_ID_PATTERN.fullmatch(item.name):
            ids.append(item.name)
    ids.sort()
    return ids


def list_campaigns() -> list[dict[str, Any]]:
    campaigns: list[dict[str, Any]] = []
    active_ids: set[str] = set()

    for campaign_id in list_campaign_ids():
        campaign = get_campaign(campaign_id)
        if campaign:
            campaigns.append(campaign)
            active_ids.add(campaign_id)

    # Include completed/archived campaigns not already in active
    for cid, entry in get_completed_campaigns().items():
        if cid not in active_ids and isinstance(entry, dict):
            campaigns.append(entry)

    campaigns.sort(key=lambda item: str(item.get("id", "")).lower(), reverse=True)
    return campaigns


def get_campaign(campaign_id: str | int) -> dict[str, Any] | None:
    # Check active campaigns folder first
    meta_path = _campaign_meta_path(campaign_id)
    if meta_path.exists():
        raw = _read_json(meta_path, {})
        if raw:
            if "id" in raw:
                raw["id"] = str(raw["id"])
            return raw

    # Fall back to completed campaigns registry
    normalized_id = _normalize_campaign_id(campaign_id)
    completed = get_completed_campaigns()
    entry = completed.get(normalized_id)
    if entry and isinstance(entry, dict):
        return {
            "id": str(entry.get("id", normalized_id)),
            "name": str(entry.get("name", "")),
            "start_time": entry.get("start_time", ""),
            "end_time": entry.get("end_time", ""),
            "target_total": int(entry.get("target_total", 0)),
            "status": "COMPLETED",
        }

    return None


def save_campaign(campaign: dict[str, Any]) -> None:
    if "id" not in campaign:
        raise HTTPException(status_code=400, detail="campaign.id is required")

    campaign_id = _normalize_campaign_id(campaign["id"])
    campaign["id"] = campaign_id

    with _io_lock:
        target = _campaign_meta_path(campaign_id)
        target.parent.mkdir(parents=True, exist_ok=True)
        _write_json(target, campaign)


def campaign_timeseries_exists(campaign_id: str | int) -> bool:
    csv_path = _campaign_timeseries_path(campaign_id)
    return csv_path.exists() and csv_path.stat().st_size > 0


def parse_timeseries_csv(csv_text: str) -> list[dict[str, Any]]:
    stream = io.StringIO(csv_text)
    reader = csv.DictReader(stream)

    if reader.fieldnames != CSV_HEADERS:
        raise HTTPException(
            status_code=400,
            detail=(
                "Invalid CSV headers. Expected exactly: "
                f"{', '.join(CSV_HEADERS)}"
            ),
        )

    rows: list[dict[str, Any]] = []
    for line_idx, row in enumerate(reader, start=2):
        raw_time = (row.get("time") or "").strip()
        raw_connected = (row.get("connected") or "").strip()
        raw_not_connected = (row.get("notconnected") or "").strip()

        if not raw_time:
            raise HTTPException(status_code=400, detail=f"Row {line_idx}: time is required")

        try:
            parsed_time = datetime.strptime(raw_time, CSV_TIME_FORMAT).replace(tzinfo=_IST)
        except ValueError as exc:
            raise HTTPException(
                status_code=400,
                detail=(
                    f"Row {line_idx}: invalid time format. "
                    f"Expected {CSV_TIME_FORMAT}"
                ),
            ) from exc

        try:
            connected = int(raw_connected)
            not_connected = int(raw_not_connected)
        except ValueError as exc:
            raise HTTPException(
                status_code=400,
                detail=f"Row {line_idx}: connected and notconnected must be integers",
            ) from exc

        if connected < 0 or not_connected < 0:
            raise HTTPException(
                status_code=400,
                detail=f"Row {line_idx}: connected and notconnected must be >= 0",
            )

        rows.append(
            {
                "time": parsed_time,
                "connected": connected,
                "notconnected": not_connected,
            }
        )

    if not rows:
        raise HTTPException(status_code=400, detail="CSV file must contain at least one row")

    rows.sort(key=lambda item: item["time"])
    return rows


def write_timeseries_rows(campaign_id: str | int, rows: list[dict[str, Any]]) -> None:
    csv_path = _campaign_timeseries_path(campaign_id)
    with _io_lock:
        csv_path.parent.mkdir(parents=True, exist_ok=True)
        with csv_path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.writer(handle)
            writer.writerow(CSV_HEADERS)
            for row in rows:
                dt_value = row["time"]
                if isinstance(dt_value, str):
                    dt_obj = datetime.strptime(dt_value, CSV_TIME_FORMAT).replace(tzinfo=_IST)
                else:
                    dt_obj = dt_value
                if dt_obj.tzinfo is None:
                    dt_obj = dt_obj.replace(tzinfo=_IST)

                if "connected" in row or "notconnected" in row or "not_connected" in row:
                    connected = int(row.get("connected", 0))
                    not_connected = int(row.get("notconnected", row.get("not_connected", 0)))
                elif "Completed" in row and "Total" in row:
                    connected = int(row["Completed"])
                    total = int(row["Total"])
                    not_connected = max(total - connected, 0)
                else:
                    raise HTTPException(
                        status_code=400,
                        detail="Timeseries rows must include connected/notconnected values",
                    )

                writer.writerow(
                    [
                        dt_obj.astimezone(_IST).strftime(CSV_TIME_FORMAT),
                        connected,
                        not_connected,
                    ]
                )


def latest_timeseries_row(campaign_id: str | int, at_time: datetime) -> dict[str, Any] | None:
    csv_path = _campaign_timeseries_path(campaign_id)
    if not csv_path.exists():
        return None

    if at_time.tzinfo is None:
        at_time = at_time.replace(tzinfo=timezone.utc)
    else:
        at_time = at_time.astimezone(timezone.utc)

    latest: dict[str, Any] | None = None

    with csv_path.open("r", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames not in (CSV_HEADERS, LEGACY_CSV_HEADERS):
            raise HTTPException(
                status_code=500,
                detail=f"Invalid CSV headers in campaign {campaign_id} timeseries file",
            )

        is_legacy = reader.fieldnames == LEGACY_CSV_HEADERS

        for row in reader:
            if not (row.get("time") or "").strip():
                continue
            timestamp = datetime.strptime(row["time"].strip(), CSV_TIME_FORMAT).replace(tzinfo=_IST)
            if timestamp <= at_time:
                if is_legacy:
                    connected = int(row["Completed"])
                    total = int(row["Total"])
                    not_connected = max(total - connected, 0)
                else:
                    connected = int(row["connected"])
                    not_connected = int(row["notconnected"])
                latest = {
                    "time": timestamp,
                    "connected": connected,
                    "notconnected": not_connected,
                }
            else:
                break

    return latest


def latest_timeseries_window(
    campaign_id: str | int,
    at_time: datetime,
    limit: int = 10,
) -> list[dict[str, Any]]:
    csv_path = _campaign_timeseries_path(campaign_id)
    if not csv_path.exists() or limit <= 0:
        return []

    if at_time.tzinfo is None:
        at_time = at_time.replace(tzinfo=timezone.utc)
    else:
        at_time = at_time.astimezone(timezone.utc)

    window: deque[dict[str, Any]] = deque(maxlen=limit)

    with csv_path.open("r", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames not in (CSV_HEADERS, LEGACY_CSV_HEADERS):
            raise HTTPException(
                status_code=500,
                detail=f"Invalid CSV headers in campaign {campaign_id} timeseries file",
            )

        is_legacy = reader.fieldnames == LEGACY_CSV_HEADERS

        for row in reader:
            if not (row.get("time") or "").strip():
                continue
            timestamp = datetime.strptime(row["time"].strip(), CSV_TIME_FORMAT).replace(tzinfo=_IST)
            if timestamp <= at_time:
                if is_legacy:
                    connected = int(row["Completed"])
                    total = int(row["Total"])
                    not_connected = max(total - connected, 0)
                else:
                    connected = int(row["connected"])
                    not_connected = int(row["notconnected"])
                window.append(
                    {
                        "time": timestamp,
                        "connected": connected,
                        "notconnected": not_connected,
                    }
                )
            else:
                break

    return list(window)


def get_completed_campaigns() -> dict[str, Any]:
    """Read all completed campaign entries from campaigns.json."""
    data = _read_json(_completed_campaigns_file, {})
    return data if isinstance(data, dict) else {}


def list_completed_campaigns(date_filter: str | None = None) -> list[dict[str, Any]]:
    """
    Return completed campaigns from campaigns.json.

    Args:
        date_filter: Optional date string ``YYYY-MM-DD``.  When provided, only
            campaigns whose ``start_time`` matches that calendar date **in IST**
            are returned.
    """
    data = get_completed_campaigns()
    result: list[dict[str, Any]] = []

    for entry in data.values():
        if not isinstance(entry, dict):
            continue

        if date_filter:
            raw_start = entry.get("start_time", "")
            try:
                dt = _parse_iso_dt(str(raw_start))           # normalise to UTC
                ist_date = dt.astimezone(_IST).date().isoformat()
                if ist_date != date_filter:
                    continue
            except Exception:
                continue

        result.append(entry)

    return result


def is_campaign_active(campaign_id: str | int) -> bool:
    """Return True if the campaign folder still exists in the active campaigns directory."""
    try:
        normalized_id = _normalize_campaign_id(campaign_id)
    except HTTPException:
        return False
    return (_campaigns_root / normalized_id).exists()


def archive_campaign(campaign_id: str | int) -> bool:
    """
    Archive a completed campaign:
    1. Read the last CSV row for the final snapshot.
    2. Save metadata + snapshot to storage/campaigns.json.
    3. Move the campaign folder from campaigns/ to past_campaigns/.
    Returns True if archived, False if folder was already gone or metadata missing.
    """
    normalized_id = _normalize_campaign_id(campaign_id)
    campaign_folder = _campaigns_root / normalized_id

    if not campaign_folder.exists():
        return False

    meta_path = campaign_folder / f"{normalized_id}.json"
    if not meta_path.exists():
        return False

    campaign = _read_json(meta_path, {})
    if not campaign:
        return False

    # Read the last row from CSV for the final snapshot
    csv_path = campaign_folder / f"{normalized_id}.csv"
    final_snapshot: dict[str, Any] = {}

    if csv_path.exists():
        last_row: dict[str, str] | None = None
        last_fieldnames: list[str] = []
        with csv_path.open("r", encoding="utf-8") as handle:
            reader = csv.DictReader(handle)
            last_fieldnames = list(reader.fieldnames or [])
            for row in reader:
                if not (row.get("time") or "").strip():
                    continue
                last_row = dict(row)

        if last_row:
            is_legacy = last_fieldnames == LEGACY_CSV_HEADERS
            if is_legacy:
                connected = int(last_row.get("Completed", 0))
                total = int(last_row.get("Total", 0))
                not_connected = max(total - connected, 0)
            else:
                connected = int(last_row.get("connected", 0))
                not_connected = int(last_row.get("notconnected", 0))

            total_uploads = connected + not_connected
            percentage = round((connected / total_uploads * 100) if total_uploads > 0 else 0.0, 2)

            raw_time = last_row.get("time", "")
            try:
                ts = datetime.strptime(raw_time, CSV_TIME_FORMAT).replace(tzinfo=_IST)
                timestamp_iso = _serialize_dt(ts)
            except ValueError:
                timestamp_iso = raw_time

            final_snapshot = {
                "campaign_id": normalized_id,
                "timestamp": timestamp_iso,
                "total_uploads": total_uploads,
                "connected": connected,
                "not_connected": not_connected,
                "percentage": percentage,
            }

    with _io_lock:
        # Re-check under lock (guard against concurrent calls)
        if not campaign_folder.exists():
            return False

        # Save to campaigns.json
        existing = _read_json(_completed_campaigns_file, {})
        if not isinstance(existing, dict):
            existing = {}

        existing[normalized_id] = {
            "id": normalized_id,
            "name": campaign.get("name", ""),
            "start_time": campaign.get("start_time", ""),
            "end_time": campaign.get("end_time", ""),
            "target_total": int(campaign.get("target_total", 0)),
            "status": "COMPLETED",
            "snapshot": final_snapshot,
        }
        _write_json(_completed_campaigns_file, existing)

        # Move folder to past_campaigns/
        _past_campaigns_root.mkdir(parents=True, exist_ok=True)
        past_folder = _past_campaigns_root / normalized_id
        if past_folder.exists():
            shutil.rmtree(str(past_folder))
        shutil.move(str(campaign_folder), str(past_folder))

    return True


def get_admin_accounts() -> list[dict[str, str]]:
    payload = _read_json(_admin_file, {"admins": []})
    admins = payload.get("admins", []) if isinstance(payload, dict) else []
    return [item for item in admins if isinstance(item, dict)]


def get_client_accounts() -> list[dict[str, str]]:
    payload = _read_json(_clients_file, {"clients": []})
    clients = payload.get("clients", []) if isinstance(payload, dict) else []
    return [item for item in clients if isinstance(item, dict)]


def storage_root_path() -> str:
    return str(_storage_root)


def campaign_time_bounds(campaign: dict[str, Any]) -> tuple[datetime, datetime]:
    start = _parse_iso_dt(campaign["start_time"])
    end = _parse_iso_dt(campaign["end_time"])
    return start, end
