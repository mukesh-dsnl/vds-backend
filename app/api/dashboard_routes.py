from typing import Optional

from fastapi import APIRouter, Depends, Query

from app.core.security import require_client
from app.schemas.campaign import CampaignResponse
from app.schemas.dashboard import ArchivedCampaignResponse, LiveStatsResponse
from app.services import campaign_service, dashboard_service

router = APIRouter(prefix="/api/client", tags=["Client Dashboard"])


@router.get("/campaigns", response_model=list[CampaignResponse])
def list_campaigns(_user: dict = Depends(require_client)):
    campaigns = campaign_service.list_campaigns()
    return [CampaignResponse(**campaign_service.campaign_to_response(item)) for item in campaigns]


@router.get("/campaigns/live", response_model=list[LiveStatsResponse])
def get_live_stats_all(_user: dict = Depends(require_client)):
    """Return cached live metrics for IN_PROGRESS campaigns only."""
    stats = dashboard_service.get_live_only_stats()
    return [LiveStatsResponse(**item) for item in stats]


@router.get("/campaigns/archived", response_model=list[ArchivedCampaignResponse])
def get_archived_campaigns(
    date: Optional[str] = Query(
        default=None,
        description="Filter by start-time date in IST — format YYYY-MM-DD (e.g. 2026-03-31)",
        pattern=r"^\d{4}-\d{2}-\d{2}$",
    ),
    _user: dict = Depends(require_client),
):
    """
    Return completed campaigns from ``storage/past_campaigns/``.

    Optionally filter by the **start date** of the campaign in IST using ``?date=YYYY-MM-DD``.
    """
    stats = dashboard_service.get_archived_stats(date_filter=date)
    return [ArchivedCampaignResponse(**item) for item in stats]


@router.get("/campaign/{campaign_id}", response_model=CampaignResponse)
def get_campaign(campaign_id: str, _user: dict = Depends(require_client)):
    campaign = campaign_service.get_campaign(campaign_id)
    return CampaignResponse(**campaign_service.campaign_to_response(campaign))


@router.get("/campaign/{campaign_id}/live", response_model=LiveStatsResponse)
def get_live_stats(campaign_id: str, _user: dict = Depends(require_client)):
    """
    Live dashboard endpoint.

    Returns the latest time-series data point whose timestamp <= NOW.
    The client should poll this every 5 seconds to get real-time updates.
    """
    stats = dashboard_service.get_live_stats(campaign_id)
    return LiveStatsResponse(**stats)
