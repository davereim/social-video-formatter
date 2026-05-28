from social_video_formatter.services.job_manager import JobManager


def test_job_status_transitions():
    manager = JobManager()
    job = manager.create_job("file123", "sample.mp4")
    assert job.status == "pending"
    retried = manager.retry_job(job.id)
    assert retried.status == "pending"
