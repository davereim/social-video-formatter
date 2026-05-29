import json
import subprocess
from pathlib import Path

from social_video_formatter.utils.logging_utils import get_logger

logger = get_logger("subtitle_detector")


class SubtitleDetector:
    def detect(self, file_path: Path) -> str:
        result = subprocess.run(
            [
                "ffprobe", "-v", "quiet",
                "-print_format", "json",
                "-show_streams",
                str(file_path),
            ],
            capture_output=True,
            text=True,
            timeout=30,
        )
        if result.returncode != 0:
            logger.warning("ffprobe subtitle check failed for %s, assuming none", file_path.name)
            return "not_detected"

        streams = json.loads(result.stdout).get("streams", [])
        has_subs = any(s.get("codec_type") == "subtitle" for s in streams)
        status = "detected" if has_subs else "not_detected"
        logger.info("Subtitle status for %s: %s", file_path.name, status)
        return status
