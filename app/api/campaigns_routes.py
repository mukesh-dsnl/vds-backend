from fastapi import APIRouter

from app.schemas.campaign import CampaignSummaryResponse
from app.schemas.dashboard import LiveStatsResponse
from app.services import campaign_service, dashboard_service

router = APIRouter(prefix="/campaigns", tags=["Campaigns"])


@router.get("", response_model=list[CampaignSummaryResponse])
def list_all_campaigns():
    """
    List all campaigns (active + completed) with basic info.

    - Active campaigns show real-time status (IN_PROGRESS / PLANNED).
    - Completed campaigns are served from the archived campaigns.json registry.
    """
    campaigns = campaign_service.list_campaigns()
    return [CampaignSummaryResponse(**campaign_service.campaign_to_summary(c)) for c in campaigns]


@router.get("/live", response_model=list[LiveStatsResponse])
def get_all_live_stats():
    """
    Return latest stats for every campaign with percentage and status.

    - IN_PROGRESS campaigns: data from 5-second live cache (CSV-backed).
    - COMPLETED campaigns: data from the archived campaigns.json snapshot
      (no CSV reading — optimised for performance).
    """
    stats = dashboard_service.get_all_live_stats()
    return [LiveStatsResponse(**item) for item in stats]
