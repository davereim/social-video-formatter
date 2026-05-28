from social_video_formatter.utils.file_utils import generate_output_filename, generate_thumbnail_filename


def test_filename_generation():
    assert generate_output_filename("market-update-may.mp4", "Instagram") == "market-update-may-Instagram.mp4"
    assert generate_thumbnail_filename("market-update-may.mp4", "YouTube") == "market-update-may-YouTube-thumbnail.jpg"
