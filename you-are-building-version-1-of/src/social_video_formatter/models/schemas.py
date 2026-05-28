from datetime import datetime
from pydantic import BaseModel


class JobCreateRequest(BaseModel):
    drive_file_id: str
    platforms: list[str] | None = None
    subtitle_mode: str = "auto"
    webhook_url: str | None = None


class JobResponse(BaseModel):
    job_id: str
    status: str
    source_file_name: str
    created_at: datetime


class JobStatusResponse(BaseModel):
    id: str
    source_file_name: str
    source_drive_file_id: str
    status: str
    subtitle_mode: str
    subtitle_status: str | None = None
    created_at: datetime
    updated_at: datetime
    completed_at: datetime | None = None
    error_summary: str | None = None
    manifest_drive_file_id: str | None = None


class WebhookTestRequest(BaseModel):
    webhook_url: str
