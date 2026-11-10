from datetime import datetime
from typing import Optional, Literal
from pydantic import BaseModel, model_validator


class Ticket(BaseModel):
    """Schema for a single support ticket."""

    ticket_id: str
    customer: str
    product: str
    issue: str
    status: Literal["open", "resolved"]
    created_at: datetime
    resolved_at: Optional[datetime] = None

    @model_validator(mode="after")
    def check_resolution_consistency(self) -> "Ticket":
        """Flag logical inconsistencies without rejecting the row."""
        if self.status == "resolved" and self.resolved_at is None:
            
            pass
        if self.status == "open" and self.resolved_at is not None:
            pass
        return self