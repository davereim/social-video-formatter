from social_video_formatter.utils.file_utils import read_json
from social_video_formatter.core.config import settings


class PlatformPresetEngine:
    def __init__(self) -> None:
        self._presets = read_json(settings.presets_path)

    def list_presets(self) -> list[dict]:
        return self._presets

    def get_preset(self, platform: str) -> dict:
        for preset in self._presets:
            if preset["platform"].lower() == platform.lower():
                return preset
        raise ValueError(f"Invalid preset for platform: {platform}")

    def default_platforms(self) -> list[str]:
        return [p["platform"] for p in self._presets if p.get("enabled_by_default", True)]
