from datetime import datetime
from typing import Optional
from pydantic import BaseModel


class ConsolidateResponse(BaseModel):
    total: int
    planned: int
    in_progress: int
    completed: int
    last_updated: Optional[datetime] = None
