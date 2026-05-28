import json
import google.auth
import google.auth.transport.requests
import requests

from social_video_formatter.core.config import settings


class CloudRunJobsService:
    def __init__(self) -> None:
        self.project = settings.gcp_project_id
        self.region = settings.gcp_region
        self.job_name = settings.cloud_run_job_name

    def run_job(self, job_id: str) -> dict:
        creds, _ = google.auth.default(scopes=["https://www.googleapis.com/auth/cloud-platform"])
        auth_req = google.auth.transport.requests.Request()
        creds.refresh(auth_req)

        url = f"https://run.googleapis.com/v2/projects/{self.project}/locations/{self.region}/jobs/{self.job_name}:run"
        body = {
            "overrides": {
                "containerOverrides": [
                    {
                        "name": "worker",
                        "env": [
                            {"name": "JOB_ID", "value": job_id}
                        ],
                    }
                ]
            }
        }
        resp = requests.post(url, headers={"Authorization": f"Bearer {creds.token}", "Content-Type": "application/json"}, data=json.dumps(body), timeout=30)
        resp.raise_for_status()
        return resp.json()
