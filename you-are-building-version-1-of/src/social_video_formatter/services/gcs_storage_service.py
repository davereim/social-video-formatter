from pathlib import Path
from google.cloud import storage

from social_video_formatter.core.config import settings


class GCSStorageService:
    def __init__(self) -> None:
        self.client = storage.Client(project=settings.gcp_project_id or None)

    def upload_output(self, local_path: Path, object_name: str) -> str:
        bucket = self.client.bucket(settings.gcs_output_bucket)
        blob = bucket.blob(object_name)
        blob.upload_from_filename(str(local_path))
        return f"gs://{settings.gcs_output_bucket}/{object_name}"

    def upload_thumbnail(self, local_path: Path, object_name: str) -> str:
        bucket = self.client.bucket(settings.gcs_thumbnails_bucket)
        blob = bucket.blob(object_name)
        blob.upload_from_filename(str(local_path))
        return f"gs://{settings.gcs_thumbnails_bucket}/{object_name}"

    def upload_manifest(self, local_path: Path, object_name: str) -> str:
        bucket = self.client.bucket(settings.gcs_manifests_bucket)
        blob = bucket.blob(object_name)
        blob.upload_from_filename(str(local_path))
        return f"gs://{settings.gcs_manifests_bucket}/{object_name}"
