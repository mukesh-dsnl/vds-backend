import enum
from dataclasses import dataclass
from datetime import datetime


class CampaignStatus(str, enum.Enum):
    PLANNED = "PLANNED"
    READY = "READY"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"


@dataclass
class Campaign:
    id: str
    name: str
    start_time: datetime
    end_time: datetime
    target_total: int
    status: CampaignStatus = CampaignStatus.PLANNED
