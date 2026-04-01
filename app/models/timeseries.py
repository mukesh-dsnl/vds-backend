from dataclasses import dataclass
from datetime import datetime


@dataclass
class CampaignTimeSeries:
    campaign_id: str
    timestamp: datetime
    connected: int
    not_connected: int
