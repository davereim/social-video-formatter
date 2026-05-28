from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "Social Video Formatter"
    app_api_key: str = "change-me"
    database_url: str = "sqlite:///./social_video_formatter.db"
    default_webhook_url: str | None = None

    google_client_id: str = ""
    google_client_secret: str = ""
    google_refresh_token: str = ""

    google_drive_input_folder_id: str = ""
    google_drive_originals_folder_id: str = ""
    google_drive_processed_folder_id: str = ""
    google_drive_thumbnails_folder_id: str = ""
    google_drive_captions_folder_id: str = ""
    google_drive_manifests_folder_id: str = ""
    google_drive_failed_folder_id: str = ""
    google_drive_needs_review_folder_id: str = ""

    gcp_project_id: str = ""
    gcp_region: str = "us-central1"
    firestore_jobs_collection: str = "jobs"
    gcs_output_bucket: str = ""
    gcs_thumbnails_bucket: str = ""
    gcs_manifests_bucket: str = ""
    cloud_run_job_name: str = "social-video-formatter-job"
    cloud_run_job_service_account: str | None = None

    watch_scan_interval_seconds: int = 30
    local_storage_path: str = "./data"
    subtitle_mode: str = "auto"
    gbp_trim_mode: str = "first_30_seconds"
    crop_anchor: str = "center"

    @property
    def presets_path(self) -> Path:
        return Path("config/platform_presets.json")

    @property
    def subtitle_template_path(self) -> Path:
        return Path("config/subtitle_template.json")


settings = Settings()
