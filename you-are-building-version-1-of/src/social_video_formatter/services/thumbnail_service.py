import subprocess
from pathlib import Path

from social_video_formatter.utils.logging_utils import get_logger

logger = get_logger("thumbnail_service")


class ThumbnailGenerator:
    def create(self, video_path: Path, thumbnail_path: Path) -> Path:
        thumbnail_path.parent.mkdir(parents=True, exist_ok=True)
        # Extract a frame at 2 seconds (falls back to frame 0 for very short clips)
        result = subprocess.run(
            [
                "ffmpeg", "-y",
                "-ss", "2",
                "-i", str(video_path),
                "-vframes", "1",
                "-q:v", "2",
                str(thumbnail_path),
            ],
            capture_output=True,
            timeout=60,
        )
        if result.returncode != 0:
            # Retry from the very first frame
            result = subprocess.run(
                [
                    "ffmpeg", "-y",
                    "-i", str(video_path),
                    "-vframes", "1",
                    "-q:v", "2",
                    str(thumbnail_path),
                ],
                capture_output=True,
                timeout=60,
            )
            if result.returncode != 0:
                raise RuntimeError(f"Thumbnail generation failed for {video_path.name}:\n{result.stderr.decode()[-1000:]}")

        logger.info("Thumbnail created: %s", thumbnail_path.name)
        return thumbnail_path
