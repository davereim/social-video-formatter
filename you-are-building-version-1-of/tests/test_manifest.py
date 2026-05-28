from pathlib import Path
from social_video_formatter.services.manifest_service import ManifestGenerator


def test_manifest_creation(tmp_path: Path):
    path = tmp_path / "market-update-may-manifest.json"
    payload = {"job_id": "abc", "source_file_name": "market-update-may.mp4", "status": "completed"}
    ManifestGenerator().create(path, payload)
    assert path.exists()
    text = path.read_text(encoding="utf-8")
    assert '"job_id": "abc"' in text
