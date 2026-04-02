from pydantic import BaseModel, Field


class CreditsResponse(BaseModel):
    total_credits: int
    used_credits: int
    available_credits: int


class CreditsUpdate(BaseModel):
    total_credits: int = Field(ge=0, description="Total credits allocated")
    used_credits: int = Field(ge=0, description="Credits consumed so far")
