import time

from social_video_formatter.core.config import settings
from social_video_formatter.services.drive_service import DriveWatcher, GoogleDriveClient
from social_video_formatter.services.job_manager import JobManager
from social_video_formatter.utils.file_utils import splitext_name, SUPPORTED_EXTENSIONS
from social_video_formatter.utils.logging_utils import get_logger


logger = get_logger("drive_watcher")


def run_watcher() -> None:
    watcher = DriveWatcher(GoogleDriveClient())
    manager = JobManager()

    while True:
        files = watcher.scan_for_new_files()
        for f in files:
            name = f.get("name", "")
            ext = splitext_name(name)[1]
            if ext not in SUPPORTED_EXTENSIONS:
                continue
            job = manager.create_job(f["id"], name, settings.subtitle_mode)
            manager.process_job(job.id)
            logger.info("Processed watched file: %s", name)
        time.sleep(settings.watch_scan_interval_seconds)


if __name__ == "__main__":
    run_watcher()
