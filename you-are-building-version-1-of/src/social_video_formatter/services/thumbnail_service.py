from pathlib import Path


class ThumbnailGenerator:
    def create(self, video_path: Path, thumbnail_path: Path) -> Path:
        thumbnail_path.parent.mkdir(parents=True, exist_ok=True)
        thumbnail_path.touch(exist_ok=True)
        return thumbnail_path
