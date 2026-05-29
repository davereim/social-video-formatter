import json
import subprocess
from pathlib import Path

from social_video_formatter.utils.logging_utils import get_logger

logger = get_logger("video_renderer")


class VideoRenderer:
    def render(self, source_video: Path, output_path: Path, preset: dict, subtitle_file: Path | None = None) -> Path:
        output_path.parent.mkdir(parents=True, exist_ok=True)

        tw, th = (int(x) for x in preset["resolution"].split("x"))
        max_duration = preset.get("max_duration_seconds")
        size_limit_mb = preset.get("absolute_file_size_limit_mb")
        target_size_mb = preset.get("target_file_size_mb")

        vf = self._build_vf(tw, th, subtitle_file)
        self._run_ffmpeg(source_video, output_path, vf, max_duration)

        if size_limit_mb:
            size_mb = output_path.stat().st_size / (1024 * 1024)
            if size_mb > size_limit_mb:
                cap_mb = target_size_mb or size_limit_mb * 0.9
                self._rerender_with_bitrate(source_video, output_path, vf, max_duration, cap_mb)

        logger.info("Rendered %s → %s", source_video.name, output_path.name)
        return output_path

    def _build_vf(self, tw: int, th: int, subtitle_file: Path | None) -> str:
        # Scale to fill (no letterbox), crop from centre
        parts = [f"scale={tw}:{th}:force_original_aspect_ratio=increase,crop={tw}:{th}"]
        if subtitle_file and subtitle_file.exists():
            # Escape colons in path for FFmpeg filter syntax
            escaped = str(subtitle_file).replace("\\", "/").replace(":", "\\:")
            parts.append(
                f"subtitles={escaped}:force_style="
                "'FontSize=18,PrimaryColour=&H00ffffff,OutlineColour=&H00000000,Outline=2,Bold=1'"
            )
        return ",".join(parts)

    def _run_ffmpeg(self, source: Path, output: Path, vf: str, max_duration: int | None) -> None:
        cmd = ["ffmpeg", "-y", "-i", str(source)]
        if max_duration:
            cmd += ["-t", str(max_duration)]
        cmd += [
            "-vf", vf,
            "-c:v", "libx264", "-crf", "23", "-preset", "medium",
            "-c:a", "aac", "-b:a", "128k",
            "-movflags", "+faststart",
            str(output),
        ]
        logger.debug("FFmpeg cmd: %s", " ".join(cmd))
        result = subprocess.run(cmd, capture_output=True, timeout=3600)
        if result.returncode != 0:
            raise RuntimeError(f"FFmpeg failed for {output.name}:\n{result.stderr.decode()[-2000:]}")

    def _rerender_with_bitrate(
        self, source: Path, output: Path, vf: str, max_duration: int | None, target_mb: float
    ) -> None:
        probe = subprocess.run(
            ["ffprobe", "-v", "quiet", "-print_format", "json", "-show_format", str(source)],
            capture_output=True, text=True, timeout=30,
        )
        duration = float(json.loads(probe.stdout)["format"]["duration"])
        if max_duration:
            duration = min(duration, float(max_duration))

        # Total budget minus audio (128kbps)
        video_bitrate_k = max(300, int((target_mb * 8 * 1024) / duration) - 128)

        cmd = ["ffmpeg", "-y", "-i", str(source)]
        if max_duration:
            cmd += ["-t", str(max_duration)]
        cmd += [
            "-vf", vf,
            "-c:v", "libx264", "-b:v", f"{video_bitrate_k}k", "-preset", "medium",
            "-c:a", "aac", "-b:a", "128k",
            "-movflags", "+faststart",
            str(output),
        ]
        logger.info("Re-encoding %s at %dk bps to meet %.1fMB limit", output.name, video_bitrate_k, target_mb)
        result = subprocess.run(cmd, capture_output=True, timeout=3600)
        if result.returncode != 0:
            raise RuntimeError(f"FFmpeg re-encode failed for {output.name}:\n{result.stderr.decode()[-2000:]}")
