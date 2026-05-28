import os

from social_video_formatter.services.job_manager import JobManager


def main() -> None:
    job_id = os.getenv("JOB_ID", "").strip()
    if not job_id:
        raise RuntimeError("JOB_ID env var is required for Cloud Run job worker")
    manager = JobManager()
    manager.process_job(job_id)


if __name__ == "__main__":
    main()
