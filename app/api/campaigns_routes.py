from typing import Optional

from fastapi import APIRouter, Query

from app.schemas.campaign import CampaignSummaryResponse
from app.schemas.dashboard import ArchivedCampaignResponse, LiveStatsResponse
from app.services import campaign_service, dashboard_service

router = APIRouter(prefix="/campaigns", tags=["Campaigns"])


@router.get("", response_model=list[CampaignSummaryResponse])
def list_all_campaigns():
    """
    List **all** campaigns (active + completed) with basic info only.

    - Active campaigns: real-time status (IN_PROGRESS / PLANNED).
    - Completed campaigns: served from the archived campaigns.json registry.
    """
    campaigns = campaign_service.list_campaigns()
    return [CampaignSummaryResponse(**campaign_service.campaign_to_summary(c)) for c in campaigns]


@router.get("/live", response_model=list[LiveStatsResponse])
def get_live_stats():
    """
    Return latest stats for **active (IN_PROGRESS / PLANNED)** campaigns only.

    Data comes from the 5-second live cache backed by the campaign CSV files
    in ``storage/campaigns/``.  Archived campaigns are excluded.
    """
    stats = dashboard_service.get_live_only_stats()
    return [LiveStatsResponse(**item) for item in stats]


@router.get("/archived", response_model=list[ArchivedCampaignResponse])
def get_archived_campaigns(
    date: Optional[str] = Query(
        default=None,
        description="Filter by start-time date in IST — format YYYY-MM-DD (e.g. 2026-03-31)",
        pattern=r"^\d{4}-\d{2}-\d{2}$",
    ),
):
    """
    Return completed campaigns from ``storage/past_campaigns/`` (indexed in campaigns.json).

    Optionally filter by the **start date** of the campaign in IST using ``?date=YYYY-MM-DD``.
    """
    stats = dashboard_service.get_archived_stats(date_filter=date)
    return [ArchivedCampaignResponse(**item) for item in stats]


@router.get("/archived/search", response_model=list[ArchivedCampaignResponse])
def search_archived_campaigns(
    date: Optional[str] = Query(
        default=None,
        description="Search by start-time date in IST — format YYYY-MM-DD (e.g. 2026-03-31)",
        pattern=r"^\d{4}-\d{2}-\d{2}$",
    ),
):
    """
    Search **completed** campaigns by date.

    Pass ``?date=YYYY-MM-DD`` to find all campaigns whose ``start_time``
    falls on that calendar day in IST (+05:30).
    Returns all completed campaigns when no date is specified.
    """
    stats = dashboard_service.get_archived_stats(date_filter=date)
    return [ArchivedCampaignResponse(**item) for item in stats]
