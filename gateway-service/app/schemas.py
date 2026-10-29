from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class JobSubmissionResponse(BaseModel):
    job_id: str
    filename: str
    status: str
    message: str
    created_at: datetime

class JobStatusResponse(BaseModel):
    job_id: str
    status: str
    error: Optional[str] = None
    summary: Optional[str] = None
    created_at: Optional[str] = None
