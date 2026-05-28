from social_video_formatter.services.preset_service import PlatformPresetEngine


def test_presets_load():
    engine = PlatformPresetEngine()
    presets = engine.list_presets()
    assert any(p["platform"] == "TikTok" for p in presets)
    gbp = engine.get_preset("Google Business Profile")
    assert gbp["strict_mode"] is True
    assert gbp["absolute_file_size_limit_mb"] == 75
