from pathlib import Path
from datetime import datetime

from social_video_formatter.utils.file_utils import write_json


class ManifestGenerator:
    def create(self, manifest_path: Path, payload: dict) -> Path:
        payload.setdefault("created_at", datetime.utcnow().isoformat())
        write_json(manifest_path, payload)
        return manifest_path
