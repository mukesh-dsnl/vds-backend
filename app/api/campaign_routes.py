from fastapi import APIRouter, Depends, File, HTTPException, UploadFile

from app.core.security import require_admin
from app.core.storage import parse_timeseries_csv, write_timeseries_rows
from app.models.campaign import CampaignStatus
from app.schemas.campaign import CampaignCreate, CampaignResponse, CampaignUpdate
from app.schemas.dashboard import LiveStatsResponse
from app.services import campaign_service, dashboard_service, simulation_service

router = APIRouter(prefix="/api/admin", tags=["Admin Campaigns"])


@router.post("/campaign", response_model=CampaignResponse, status_code=201)
def create_campaign(data: CampaignCreate, _user: dict = Depends(require_admin)):
    """Create a new campaign with its simulation configuration."""
    campaign = campaign_service.create_campaign(data)
    return CampaignResponse(**campaign_service.campaign_to_response(campaign))


@router.get("/campaigns", response_model=list[CampaignResponse])
def list_campaigns(_user: dict = Depends(require_admin)):
    """List all campaigns."""
    campaigns = campaign_service.list_campaigns()
    return [CampaignResponse(**campaign_service.campaign_to_response(item)) for item in campaigns]


@router.get("/campaign/{campaign_id}", response_model=CampaignResponse)
def get_campaign(campaign_id: str, _user: dict = Depends(require_admin)):
    """Fetch a single campaign by ID."""
    campaign = campaign_service.get_campaign(campaign_id)
    return CampaignResponse(**campaign_service.campaign_to_response(campaign))


@router.put("/campaign/{campaign_id}", response_model=CampaignResponse)
def update_campaign(campaign_id: str, data: CampaignUpdate, _user: dict = Depends(require_admin)):
    """Update campaign details and configuration before simulation generation."""
    campaign = campaign_service.update_campaign(campaign_id, data)
    return CampaignResponse(**campaign_service.campaign_to_response(campaign))


@router.post("/campaign/{campaign_id}/generate")
def generate_simulation(campaign_id: str, _user: dict = Depends(require_admin)):
    """Trigger time-series generation for a campaign."""
    total_rows = simulation_service.generate_time_series(campaign_id)
    return {
        "message": f"Simulation generated successfully for campaign {campaign_id}",
        "rows_written": total_rows,
    }


@router.post("/campaign/{campaign_id}/timeseries/upload")
async def upload_timeseries(campaign_id: str, file: UploadFile = File(...), _user: dict = Depends(require_admin)):
    """Upload campaign CSV with headers: time,connected,notconnected."""
    campaign_service.get_campaign(campaign_id)

    try:
        csv_text = (await file.read()).decode("utf-8")
    except UnicodeDecodeError as exc:
        raise HTTPException(status_code=400, detail="CSV must be UTF-8 encoded") from exc

    rows = parse_timeseries_csv(csv_text)
    write_timeseries_rows(campaign_id, rows)
    campaign_service.update_campaign_status(campaign_id, CampaignStatus.READY)

    return {
        "message": f"CSV uploaded successfully for campaign {campaign_id}",
        "rows_written": len(rows),
        "columns": ["time", "connected", "notconnected"],
    }


@router.get("/campaign/{campaign_id}/live", response_model=LiveStatsResponse)
def get_live_stats(campaign_id: str, _user: dict = Depends(require_admin)):
    stats = dashboard_service.get_live_stats(campaign_id)
    return LiveStatsResponse(**stats)


@router.get("/campaigns/live", response_model=list[LiveStatsResponse])
def get_live_stats_all(_user: dict = Depends(require_admin)):
    stats = dashboard_service.get_all_live_stats()
    return [LiveStatsResponse(**item) for item in stats]
