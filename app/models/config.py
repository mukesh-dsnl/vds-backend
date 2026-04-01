from dataclasses import dataclass


@dataclass
class CampaignConfig:
    id: str
    campaign_id: str
    connected_ratio: float = 0.6
    not_connected_ratio: float = 0.25
    pending_ratio: float = 0.15
    curve_type: str = "sigmoid"
    noise_level: float = 0.02
    interval_seconds: int = 5
