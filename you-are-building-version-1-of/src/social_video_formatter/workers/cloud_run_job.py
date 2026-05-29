import os

from social_video_formatter.services.job_manager import JobManager
from social_video_formatter.utils.logging_utils import get_logger

logger = get_logger("cloud_run_job")


def main() -> None:
    job_id = os.getenv("JOB_ID", "").strip()
    if not job_id:
        raise RuntimeError("JOB_ID env var is required for Cloud Run job worker")

    manager = JobManager()

    # Read the platforms list stored in Firestore when the job was created.
    # The worker starts in a fresh container so it has no local state.
    platforms = None
    if manager.firestore:
        data = manager.firestore.get_job(job_id)
        if data:
            platforms = data.get("platforms") or None
            if platforms:
                logger.info("Running job %s for platforms: %s", job_id, platforms)

    manager.process_job(job_id, platforms=platforms)


if __name__ == "__main__":
    main()
