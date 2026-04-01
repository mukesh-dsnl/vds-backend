from datetime import datetime
from typing import Optional
from pydantic import BaseModel, field_validator, model_validator


# ── Request Schemas ──────────────────────────────────────────────────────────


class CampaignConfigCreate(BaseModel):
    """Configuration for simulation parameters."""

    connected_ratio: float = 0.6
    not_connected_ratio: float = 0.25
    pending_ratio: float = 0.15
    curve_type: str = "sigmoid"
    noise_level: float = 0.02
    interval_seconds: int = 5

    @model_validator(mode="after")
    def validate_ratios_sum(self):
        total = round(self.connected_ratio + self.not_connected_ratio + self.pending_ratio, 10)
        if abs(total - 1.0) > 1e-6:
            raise ValueError(
                f"Ratios must sum to 1.0 (got {total}): "
                f"connected={self.connected_ratio}, "
                f"not_connected={self.not_connected_ratio}, "
                f"pending={self.pending_ratio}"
            )
        return self

    @field_validator("interval_seconds")
    @classmethod
    def interval_must_be_positive(cls, v: int) -> int:
        if v <= 0:
            raise ValueError("interval_seconds must be > 0")
        return v

    @field_validator("noise_level")
    @classmethod
    def noise_must_be_non_negative(cls, v: float) -> float:
        if v < 0:
            raise ValueError("noise_level must be >= 0")
        return v


class CampaignCreate(BaseModel):
    """Payload for creating a new campaign."""

    campaign_id: str
    name: str
    start_time: datetime
    end_time: datetime
    target_total: int
    config: CampaignConfigCreate = CampaignConfigCreate()

    @field_validator("campaign_id")
    @classmethod
    def validate_campaign_id(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("campaign_id is required")
        if len(normalized) > 10:
            raise ValueError("campaign_id length must be <= 10")
        for char in normalized:
            if not (char.isalnum() or char in "_-"):
                raise ValueError(
                    "campaign_id supports only letters, numbers, underscore, and hyphen"
                )
        return normalized

    @model_validator(mode="after")
    def start_before_end(self):
        if self.start_time >= self.end_time:
            raise ValueError("start_time must be before end_time")
        return self

    @field_validator("target_total")
    @classmethod
    def target_must_be_positive(cls, v: int) -> int:
        if v <= 0:
            raise ValueError("target_total must be > 0")
        return v


class CampaignConfigUpdate(BaseModel):
    connected_ratio: float
    not_connected_ratio: float
    pending_ratio: float
    curve_type: str
    noise_level: float
    interval_seconds: int

    @model_validator(mode="after")
    def validate_ratios_sum(self):
        total = round(self.connected_ratio + self.not_connected_ratio + self.pending_ratio, 10)
        if abs(total - 1.0) > 1e-6:
            raise ValueError(
                f"Ratios must sum to 1.0 (got {total}): "
                f"connected={self.connected_ratio}, "
                f"not_connected={self.not_connected_ratio}, "
                f"pending={self.pending_ratio}"
            )
        return self

    @field_validator("interval_seconds")
    @classmethod
    def interval_must_be_positive(cls, v: int) -> int:
        if v <= 0:
            raise ValueError("interval_seconds must be > 0")
        return v

    @field_validator("noise_level")
    @classmethod
    def noise_must_be_non_negative(cls, v: float) -> float:
        if v < 0:
            raise ValueError("noise_level must be >= 0")
        return v


class CampaignUpdate(BaseModel):
    name: str
    start_time: datetime
    end_time: datetime
    target_total: int
    config: CampaignConfigUpdate

    @model_validator(mode="after")
    def start_before_end(self):
        if self.start_time >= self.end_time:
            raise ValueError("start_time must be before end_time")
        return self

    @field_validator("target_total")
    @classmethod
    def target_must_be_positive(cls, v: int) -> int:
        if v <= 0:
            raise ValueError("target_total must be > 0")
        return v


# ── Response Schemas ─────────────────────────────────────────────────────────


class CampaignConfigResponse(BaseModel):
    id: str
    campaign_id: str
    connected_ratio: float
    not_connected_ratio: float
    pending_ratio: float
    curve_type: str
    noise_level: float
    interval_seconds: int

    class Config:
        from_attributes = True


class CampaignResponse(BaseModel):
    id: str
    name: str
    start_time: datetime
    end_time: datetime
    target_total: int
    status: str
    config: Optional[CampaignConfigResponse] = None

    class Config:
        from_attributes = True
