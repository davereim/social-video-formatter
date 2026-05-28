from pathlib import Path


class VideoAnalyzer:
    def analyze(self, file_path: Path) -> dict:
        # V1 placeholder metadata. Replace with ffprobe integration in production.
        return {
            "original_filename": file_path.name,
            "file_extension": file_path.suffix.lower(),
            "file_size_mb": 10.0,
            "duration_seconds": 30.0,
            "width": 1920,
            "height": 1080,
            "aspect_ratio": "16:9",
            "frame_rate": 30,
            "video_codec": "h264",
            "audio_codec": "aac",
            "has_audio": True,
            "estimated_loudness": None,
            "orientation": "horizontal",
            "bitrate": 4000000,
            "source_shape": "horizontal",
        }
