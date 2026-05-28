from pathlib import Path


class TranscriptionEngine:
    def transcribe(self, video_path: Path, captions_dir: Path, base_name: str) -> dict:
        captions_dir.mkdir(parents=True, exist_ok=True)
        srt_path = captions_dir / f"{base_name}.srt"
        vtt_path = captions_dir / f"{base_name}.vtt"
        srt_path.write_text("1\n00:00:00,000 --> 00:00:02,000\nSample subtitle\n", encoding="utf-8")
        vtt_path.write_text("WEBVTT\n\n00:00.000 --> 00:02.000\nSample subtitle\n", encoding="utf-8")
        return {"srt": srt_path, "vtt": vtt_path}
