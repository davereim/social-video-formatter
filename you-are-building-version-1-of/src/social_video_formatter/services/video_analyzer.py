import json
import math
import subprocess
from pathlib import Path

from social_video_formatter.utils.logging_utils import get_logger

logger = get_logger("video_analyzer")


class VideoAnalyzer:
    def analyze(self, file_path: Path) -> dict:
        result = subprocess.run(
            [
                "ffprobe", "-v", "quiet",
                "-print_format", "json",
                "-show_format",
                "-show_streams",
                str(file_path),
            ],
            capture_output=True,
            text=True,
            timeout=60,
        )
        if result.returncode != 0:
            raise RuntimeError(f"ffprobe failed: {result.stderr}")

        data = json.loads(result.stdout)
        streams = data.get("streams", [])
        fmt = data.get("format", {})

        video = next((s for s in streams if s.get("codec_type") == "video"), {})
        audio = next((s for s in streams if s.get("codec_type") == "audio"), None)

        width = int(video.get("width", 0))
        height = int(video.get("height", 0))
        duration = float(fmt.get("duration") or video.get("duration") or 0)

        fr_str = video.get("r_frame_rate", "30/1")
        num, den = fr_str.split("/")
        frame_rate = round(int(num) / int(den), 3) if int(den) else 30.0

        if width and height:
            gcd = math.gcd(width, height)
            aspect_ratio = f"{width // gcd}:{height // gcd}"
        else:
            aspect_ratio = "unknown"

        if width > height:
            orientation, source_shape = "horizontal", "horizontal"
        elif height > width:
            orientation, source_shape = "vertical", "vertical"
        else:
            orientation, source_shape = "square", "square"

        file_size_bytes = int(fmt.get("size") or file_path.stat().st_size)

        logger.info(
            "Analyzed %s: %dx%d %.2fs %.1fMB",
            file_path.name, width, height, duration, file_size_bytes / (1024 * 1024),
        )

        return {
            "original_filename": file_path.name,
            "file_extension": file_path.suffix.lower(),
            "file_size_mb": round(file_size_bytes / (1024 * 1024), 2),
            "duration_seconds": round(duration, 2),
            "width": width,
            "height": height,
            "aspect_ratio": aspect_ratio,
            "frame_rate": frame_rate,
            "video_codec": video.get("codec_name", "unknown"),
            "audio_codec": audio.get("codec_name") if audio else None,
            "has_audio": audio is not None,
            "estimated_loudness": None,
            "orientation": orientation,
            "bitrate": int(fmt.get("bit_rate") or 0),
            "source_shape": source_shape,
        }
