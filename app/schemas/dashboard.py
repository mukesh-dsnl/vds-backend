from datetime import datetime
from typing import Optional
from pydantic import BaseModel


class LiveStatsResponse(BaseModel):
    """Response for the live dashboard endpoint."""

    campaign_id: str
    timestamp: datetime
    total_uploads: int
    connected: int
    not_connected: int
    percentage: float = 0.0
    status: str = ""

    class Config:
        from_attributes = True


class ArchivedCampaignResponse(BaseModel):
    """Response for a completed/archived campaign with its final snapshot."""

    campaign_id: str
    name: str
    start_time: datetime
    end_time: datetime
    target_total: int
    timestamp: datetime   # time of the final snapshot row
    total_uploads: int
    connected: int
    not_connected: int
    percentage: float
    status: str = "COMPLETED"

    class Config:
        from_attributes = True


class CampaignSummaryResponse(BaseModel):
    """Lightweight campaign info response without config details."""

    id: str
    name: str
    start_time: datetime
    end_time: datetime
    target_total: int
    status: str

    class Config:
        from_attributes = True


class CampaignStatusResponse(BaseModel):
    """Lightweight response showing campaign status and timing."""

    id: str
    name: str
    status: str
    start_time: datetime
    end_time: datetime
    target_total: int
    current_total: Optional[int] = None
    progress_pct: Optional[float] = None
