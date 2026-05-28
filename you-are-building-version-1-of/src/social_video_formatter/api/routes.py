from datetime import datetime
from pathlib import Path
from urllib.parse import urlencode
import secrets

import requests
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from fastapi.responses import FileResponse

from social_video_formatter.core.auth import require_api_key
from social_video_formatter.core.config import settings
from social_video_formatter.core.database import SessionLocal
from social_video_formatter.models.db_models import AppSetting
from social_video_formatter.models.schemas import JobCreateRequest, WebhookTestRequest
from social_video_formatter.services.job_manager import JobManager
from social_video_formatter.services.drive_service import GoogleDriveClient
from social_video_formatter.services.preset_service import PlatformPresetEngine
from social_video_formatter.services.webhook_service import WebhookNotifier
from social_video_formatter.services.cloud_run_jobs_service import CloudRunJobsService
from social_video_formatter.services.firestore_status_service import FirestoreJobStore

router = APIRouter()
manager = JobManager()
presets = PlatformPresetEngine()
webhooks = WebhookNotifier()
cloud_run = CloudRunJobsService() if settings.gcp_project_id else None
firestore_store = FirestoreJobStore() if settings.gcp_project_id else None
ENV_PATH = Path(".env")
ENV_KEYS = [
    "GOOGLE_CLIENT_ID", "GOOGLE_CLIENT_SECRET", "GOOGLE_REFRESH_TOKEN",
    "GOOGLE_DRIVE_INPUT_FOLDER_ID", "GOOGLE_DRIVE_ORIGINALS_FOLDER_ID", "GOOGLE_DRIVE_PROCESSED_FOLDER_ID",
    "GOOGLE_DRIVE_THUMBNAILS_FOLDER_ID", "GOOGLE_DRIVE_CAPTIONS_FOLDER_ID", "GOOGLE_DRIVE_MANIFESTS_FOLDER_ID",
    "GOOGLE_DRIVE_FAILED_FOLDER_ID", "GOOGLE_DRIVE_NEEDS_REVIEW_FOLDER_ID", "APP_API_KEY",
    "GCP_PROJECT_ID", "GCP_REGION", "FIRESTORE_JOBS_COLLECTION", "GCS_OUTPUT_BUCKET", "GCS_THUMBNAILS_BUCKET",
    "GCS_MANIFESTS_BUCKET", "CLOUD_RUN_JOB_NAME", "CLOUD_RUN_JOB_SERVICE_ACCOUNT"
]
GOOGLE_SCOPE = "https://www.googleapis.com/auth/drive"
REDIRECT_URI = "urn:ietf:wg:oauth:2.0:oob"


def _read_env_map() -> dict:
    values = {k: "" for k in ENV_KEYS}
    if not ENV_PATH.exists():
        return values
    for line in ENV_PATH.read_text(encoding="utf-8").splitlines():
        if "=" not in line or line.strip().startswith("#"):
            continue
        key, val = line.split("=", 1)
        if key in values:
            values[key] = val
    return values


def _save_env_map(values: dict) -> None:
    existing = {}
    if ENV_PATH.exists():
        for line in ENV_PATH.read_text(encoding="utf-8").splitlines():
            if "=" in line and not line.strip().startswith("#"):
                key, val = line.split("=", 1)
                existing[key] = val
    for key in ENV_KEYS:
        if key in values:
            existing[key] = str(values.get(key, ""))
    lines = [f"{k}={v}" for k, v in existing.items()]
    ENV_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _save_settings_to_db(values: dict) -> None:
    with SessionLocal() as db:
        for key, value in values.items():
            row = db.get(AppSetting, key)
            if row:
                row.value = str(value)
                row.updated_at = datetime.utcnow()
            else:
                db.add(AppSetting(key=key, value=str(value), updated_at=datetime.utcnow()))
        db.commit()


def _load_settings_from_db() -> dict:
    with SessionLocal() as db:
        out = {}
        for key in ENV_KEYS:
            row = db.get(AppSetting, key)
            if row:
                out[key] = row.value
        return out


@router.get("/health")
def health() -> dict:
    return {"status": "ok", "service": "social-video-formatter", "cloud_mode": bool(settings.gcp_project_id)}


@router.get("/ui")
def basic_ui() -> FileResponse:
    return FileResponse(Path("ui/index.html"))


@router.get("/config/env")
def get_env_config() -> dict:
    values = _read_env_map()
    db_values = _load_settings_from_db()
    for key, val in db_values.items():
        if val:
            values[key] = val
    return values


@router.post("/config/env")
def save_env_config(payload: dict) -> dict:
    to_save = {k: str(payload.get(k, "")) for k in ENV_KEYS if k in payload}
    _save_env_map(to_save)
    _save_settings_to_db(to_save)
    return {"status": "saved", "message": "Config saved. Restart API to apply changes."}


@router.post("/oauth/google/start")
def oauth_google_start(payload: dict) -> dict:
    client_id = (payload.get("GOOGLE_CLIENT_ID") or "").strip()
    if not client_id:
        raise HTTPException(status_code=400, detail="GOOGLE_CLIENT_ID is required")
    state = secrets.token_urlsafe(16)
    query = urlencode({"client_id": client_id, "redirect_uri": REDIRECT_URI, "response_type": "code", "scope": GOOGLE_SCOPE, "access_type": "offline", "prompt": "consent", "state": state})
    return {"auth_url": f"https://accounts.google.com/o/oauth2/v2/auth?{query}", "state": state}


@router.post("/oauth/google/exchange")
def oauth_google_exchange(payload: dict) -> dict:
    code = (payload.get("code") or "").strip()
    client_id = (payload.get("GOOGLE_CLIENT_ID") or "").strip()
    client_secret = (payload.get("GOOGLE_CLIENT_SECRET") or "").strip()
    if not code or not client_id or not client_secret:
        raise HTTPException(status_code=400, detail="code, GOOGLE_CLIENT_ID, and GOOGLE_CLIENT_SECRET are required")
    resp = requests.post("https://oauth2.googleapis.com/token", data={"code": code, "client_id": client_id, "client_secret": client_secret, "redirect_uri": REDIRECT_URI, "grant_type": "authorization_code"}, timeout=20)
    if not resp.ok:
        raise HTTPException(status_code=400, detail=f"Token exchange failed: {resp.text}")
    refresh_token = resp.json().get("refresh_token", "")
    if not refresh_token:
        raise HTTPException(status_code=400, detail="No refresh_token returned")
    save_values = {"GOOGLE_CLIENT_ID": client_id, "GOOGLE_CLIENT_SECRET": client_secret, "GOOGLE_REFRESH_TOKEN": refresh_token}
    _save_env_map(save_values)
    _save_settings_to_db(save_values)
    return {"status": "saved", "message": "Refresh token saved."}


@router.post("/jobs", dependencies=[Depends(require_api_key)])
def create_job(payload: JobCreateRequest, bg: BackgroundTasks, run_mode: str = Query("cloud", pattern="^(cloud|local)$")) -> dict:
    source_file_name = f"{payload.drive_file_id}.mp4"
    try:
        source_file_name = GoogleDriveClient().get_file_metadata(payload.drive_file_id).get("name", source_file_name)
    except Exception:
        pass

    job = manager.create_job(payload.drive_file_id, source_file_name, payload.subtitle_mode)

    if run_mode == "local" or not cloud_run:
        bg.add_task(manager.process_job, job.id, payload.platforms, payload.webhook_url)
        return {"job_id": job.id, "status": job.status, "execution": "local_background"}

    exec_resp = cloud_run.run_job(job.id)
    if firestore_store:
        firestore_store.update_job(job.id, {"status": "pending", "execution": "cloud_run_job", "platforms": payload.platforms or []})
    return {"job_id": job.id, "status": job.status, "execution": "cloud_run_job", "cloud_run": exec_resp}


@router.get("/jobs", dependencies=[Depends(require_api_key)])
def list_jobs(source: str = Query("firestore", pattern="^(firestore|sqlite)$")) -> list[dict]:
    if source == "firestore" and firestore_store:
        return firestore_store.list_jobs()
    return [{"id": j.id, "source_file_name": j.source_file_name, "source_drive_file_id": j.source_drive_file_id, "status": j.status, "created_at": j.created_at} for j in manager.list_jobs()]


@router.get("/jobs/{job_id}", dependencies=[Depends(require_api_key)])
def get_job(job_id: str, source: str = Query("firestore", pattern="^(firestore|sqlite)$")) -> dict:
    if source == "firestore" and firestore_store:
        job = firestore_store.get_job(job_id)
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")
        return {"id": job_id, **job}
    try:
        j = manager.get_job(job_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="Job not found")
    return {"id": j.id, "source_file_name": j.source_file_name, "source_drive_file_id": j.source_drive_file_id, "status": j.status, "subtitle_mode": j.subtitle_mode, "subtitle_status": j.subtitle_status, "error_summary": j.error_summary, "manifest_drive_file_id": j.manifest_drive_file_id, "created_at": j.created_at, "updated_at": j.updated_at, "completed_at": j.completed_at}


@router.post("/jobs/{job_id}/retry", dependencies=[Depends(require_api_key)])
def retry_job(job_id: str, bg: BackgroundTasks) -> dict:
    try:
        job = manager.retry_job(job_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="Job not found")
    bg.add_task(manager.process_job, job.id)
    return {"job_id": job.id, "status": job.status}


@router.get("/jobs/{job_id}/outputs", dependencies=[Depends(require_api_key)])
def job_outputs(job_id: str) -> list[dict]:
    return [{"platform": o.platform, "file_name": o.file_name, "drive_file_id": o.drive_file_id, "thumbnail_drive_file_id": o.thumbnail_drive_file_id, "status": o.status} for o in manager.list_outputs(job_id)]


@router.get("/presets", dependencies=[Depends(require_api_key)])
def list_presets() -> list[dict]:
    return presets.list_presets()


@router.get("/presets/{platform}", dependencies=[Depends(require_api_key)])
def get_preset(platform: str) -> dict:
    try:
        return presets.get_preset(platform)
    except ValueError as ex:
        raise HTTPException(status_code=404, detail=str(ex))


@router.post("/webhooks/test", dependencies=[Depends(require_api_key)])
def test_webhook(payload: WebhookTestRequest) -> dict:
    status, code = webhooks.send(payload.webhook_url, {"event": "webhook.test", "status": "ok"})
    return {"status": status, "response_code": code}


@router.post("/scan", dependencies=[Depends(require_api_key)])
def scan() -> dict:
    return {"status": "not_used_in_cloud_run_jobs", "note": "Use scheduler or external trigger to create /jobs."}


@router.post("/jobs/{job_id}/cancel", dependencies=[Depends(require_api_key)])
def cancel_job(job_id: str) -> dict:
    j = manager.get_job(job_id)
    if j.status in {"rendering", "uploading", "transcribing", "downloading", "analyzing"}:
        raise HTTPException(status_code=409, detail="Cannot cancel active processing job")
    with SessionLocal() as db:
        job = db.get(type(j), job_id)
        job.status = "cancelled"
        job.updated_at = datetime.utcnow()
        db.commit()
    if firestore_store:
        firestore_store.update_job(job_id, {"status": "cancelled"})
    return {"job_id": job_id, "status": "cancelled"}