from dataclasses import dataclass
from pathlib import Path
import mimetypes

import requests

from social_video_formatter.core.config import settings


@dataclass
class FolderMap:
    input_folder: str
    originals_folder: str
    processed_folder: str
    thumbnails_folder: str
    captions_folder: str
    manifests_folder: str
    failed_folder: str
    needs_review_folder: str


class DriveWatcher:
    def __init__(self, drive_client: "GoogleDriveClient"):
        self.drive_client = drive_client

    def scan_for_new_files(self) -> list[dict]:
        return self.drive_client.list_video_files(settings.google_drive_input_folder_id)


class GoogleDriveClient:
    def __init__(self) -> None:
        self.storage_root = Path(settings.local_storage_path)
        self._token: str | None = None

    def _refresh_access_token(self) -> str:
        if self._token:
            return self._token
        resp = requests.post(
            "https://oauth2.googleapis.com/token",
            data={
                "client_id": settings.google_client_id,
                "client_secret": settings.google_client_secret,
                "refresh_token": settings.google_refresh_token,
                "grant_type": "refresh_token",
            },
            timeout=20,
        )
        resp.raise_for_status()
        self._token = resp.json()["access_token"]
        return self._token

    def _headers(self) -> dict:
        return {"Authorization": f"Bearer {self._refresh_access_token()}"}

    def list_video_files(self, folder_id: str) -> list[dict]:
        q = (
            f"'{folder_id}' in parents and trashed=false and "
            "(mimeType='video/mp4' or mimeType='video/quicktime' or name contains '.m4v')"
        )
        resp = requests.get(
            "https://www.googleapis.com/drive/v3/files",
            headers=self._headers(),
            params={"q": q, "pageSize": 100, "fields": "files(id,name,mimeType,size)"},
            timeout=20,
        )
        resp.raise_for_status()
        return resp.json().get("files", [])

    def get_file_metadata(self, file_id: str) -> dict:
        resp = requests.get(
            f"https://www.googleapis.com/drive/v3/files/{file_id}",
            headers=self._headers(),
            params={"fields": "id,name,mimeType,size"},
            timeout=20,
        )
        resp.raise_for_status()
        return resp.json()

    def download_file(self, file_id: str, destination: Path) -> Path:
        destination.parent.mkdir(parents=True, exist_ok=True)
        resp = requests.get(
            f"https://www.googleapis.com/drive/v3/files/{file_id}",
            headers=self._headers(),
            params={"alt": "media"},
            timeout=300,
            stream=True,
        )
        resp.raise_for_status()
        with destination.open("wb") as f:
            for chunk in resp.iter_content(chunk_size=1024 * 1024):
                if chunk:
                    f.write(chunk)
        return destination

    def upload_file(self, path: Path, folder_id: str, target_name: str) -> str:
        metadata = {"name": target_name, "parents": [folder_id]}
        mime = mimetypes.guess_type(target_name)[0] or "application/octet-stream"
        session_resp = requests.post(
            "https://www.googleapis.com/upload/drive/v3/files?uploadType=resumable",
            headers={**self._headers(), "Content-Type": "application/json; charset=UTF-8"},
            json=metadata,
            timeout=20,
        )
        session_resp.raise_for_status()
        upload_url = session_resp.headers.get("Location")
        if not upload_url:
            raise RuntimeError("Google Drive upload session did not return a Location URL")
        with path.open("rb") as f:
            put_resp = requests.put(upload_url, headers={"Content-Type": mime}, data=f, timeout=300)
        put_resp.raise_for_status()
        return put_resp.json().get("id", "")

    def move_or_copy(self, file_id: str, target_folder_id: str) -> None:
        requests.post(
            f"https://www.googleapis.com/drive/v3/files/{file_id}/copy",
            headers={**self._headers(), "Content-Type": "application/json"},
            json={"parents": [target_folder_id]},
            timeout=20,
        ).raise_for_status()