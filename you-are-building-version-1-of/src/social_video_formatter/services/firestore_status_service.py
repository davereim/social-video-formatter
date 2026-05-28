from datetime import datetime
from google.cloud import firestore

from social_video_formatter.core.config import settings


class FirestoreJobStore:
    def __init__(self) -> None:
        self.client = firestore.Client(project=settings.gcp_project_id or None)
        self.collection = self.client.collection(settings.firestore_jobs_collection)

    def create_job(self, job_id: str, payload: dict) -> None:
        payload = {**payload, "created_at": datetime.utcnow().isoformat(), "updated_at": datetime.utcnow().isoformat()}
        self.collection.document(job_id).set(payload)

    def update_job(self, job_id: str, updates: dict) -> None:
        updates = {**updates, "updated_at": datetime.utcnow().isoformat()}
        self.collection.document(job_id).set(updates, merge=True)

    def get_job(self, job_id: str) -> dict | None:
        snap = self.collection.document(job_id).get()
        return snap.to_dict() if snap.exists else None

    def list_jobs(self, limit: int = 100) -> list[dict]:
        docs = self.collection.order_by("created_at", direction=firestore.Query.DESCENDING).limit(limit).stream()
        out = []
        for d in docs:
            v = d.to_dict()
            v["id"] = d.id
            out.append(v)
        return out
