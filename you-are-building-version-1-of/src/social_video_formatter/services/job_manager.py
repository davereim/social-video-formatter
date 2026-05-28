from __future__ import annotations

from datetime import datetime
from pathlib import Path
from uuid import uuid4

from sqlalchemy import select

from social_video_formatter.core.config import settings
from social_video_formatter.core.database import SessionLocal, init_db
from social_video_formatter.models.db_models import Job, JobError, JobOutput, WebhookEvent
from social_video_formatter.services.drive_service import GoogleDriveClient
from social_video_formatter.services.manifest_service import ManifestGenerator
from social_video_formatter.services.preset_service import PlatformPresetEngine
from social_video_formatter.services.subtitle_detector import SubtitleDetector
from social_video_formatter.services.thumbnail_service import ThumbnailGenerator
from social_video_formatter.services.transcription_service import TranscriptionEngine
from social_video_formatter.services.video_analyzer import VideoAnalyzer
from social_video_formatter.services.video_renderer import VideoRenderer
from social_video_formatter.services.webhook_service import WebhookNotifier
from social_video_formatter.services.firestore_status_service import FirestoreJobStore
from social_video_formatter.services.gcs_storage_service import GCSStorageService
from social_video_formatter.utils.file_utils import generate_output_filename, generate_thumbnail_filename, splitext_name
from social_video_formatter.utils.logging_utils import get_logger


logger = get_logger("job_manager")
VALID_STATUSES = {
    "pending", "downloading", "analyzing", "transcribing", "rendering", "uploading", "completed", "failed", "needs_review", "cancelled"
}


class JobManager:
    def __init__(self) -> None:
        init_db()
        self.drive = GoogleDriveClient()
        self.presets = PlatformPresetEngine()
        self.analyzer = VideoAnalyzer()
        self.subtitle_detector = SubtitleDetector()
        self.transcriber = TranscriptionEngine()
        self.renderer = VideoRenderer()
        self.thumbnail = ThumbnailGenerator()
        self.manifest = ManifestGenerator()
        self.webhooks = WebhookNotifier()
        self.storage_root = Path(settings.local_storage_path)
        self.cloud_mode = bool(settings.gcs_output_bucket and settings.gcs_thumbnails_bucket and settings.gcs_manifests_bucket)
        self.gcs = GCSStorageService() if self.cloud_mode else None
        self.firestore = FirestoreJobStore() if settings.gcp_project_id else None

    def create_job(self, source_drive_file_id: str, source_file_name: str, subtitle_mode: str = "auto") -> Job:
        with SessionLocal() as db:
            job = Job(
                id=str(uuid4()),
                source_file_name=source_file_name,
                source_drive_file_id=source_drive_file_id,
                status="pending",
                subtitle_mode=subtitle_mode,
            )
            db.add(job)
            db.commit()
            db.refresh(job)
            if self.firestore:
                self.firestore.create_job(
                    job.id,
                    {
                        "source_file_name": source_file_name,
                        "source_drive_file_id": source_drive_file_id,
                        "status": "pending",
                        "subtitle_mode": subtitle_mode,
                    },
                )
            logger.info("Job created: %s", job.id)
            return job

    def list_jobs(self) -> list[Job]:
        with SessionLocal() as db:
            return list(db.scalars(select(Job).order_by(Job.created_at.desc())))

    def get_job(self, job_id: str) -> Job:
        with SessionLocal() as db:
            job = db.get(Job, job_id)
            if not job:
                raise ValueError("Job not found")
            return job

    def retry_job(self, job_id: str) -> Job:
        with SessionLocal() as db:
            job = db.get(Job, job_id)
            if not job:
                raise ValueError("Job not found")
            job.status = "pending"
            job.error_summary = None
            job.updated_at = datetime.utcnow()
            db.commit()
            db.refresh(job)
            if self.firestore:
                self.firestore.update_job(job.id, {"status": "pending", "error_summary": None})
            return job

    def list_outputs(self, job_id: str) -> list[JobOutput]:
        with SessionLocal() as db:
            return list(db.scalars(select(JobOutput).where(JobOutput.job_id == job_id)))

    def process_job(self, job_id: str, platforms: list[str] | None = None, webhook_url: str | None = None) -> None:
        with SessionLocal() as db:
            job = db.get(Job, job_id)
            if not job:
                raise ValueError("Job not found")

            chosen_platforms = platforms or self.presets.default_platforms()
            stem, ext = splitext_name(job.source_file_name)
            if ext not in {".mp4", ".mov", ".m4v"}:
                self._fail(db, job, "unsupported_file_type", f"Unsupported file type: {ext}")
                return

            try:
                self._set_status(db, job, "downloading")
                source_path = self.storage_root / "downloads" / job.source_file_name
                self.drive.download_file(job.source_drive_file_id, source_path)
                self.drive.move_or_copy(job.source_drive_file_id, settings.google_drive_originals_folder_id)

                self._set_status(db, job, "analyzing")
                source_metadata = self.analyzer.analyze(source_path)
                subtitle_status = self.subtitle_detector.detect(source_path)
                job.subtitle_status = subtitle_status
                db.commit()
                if self.firestore:
                    self.firestore.update_job(job.id, {"subtitle_status": subtitle_status, "source_metadata": source_metadata})

                transcript = None
                if self._should_transcribe(job.subtitle_mode, subtitle_status):
                    self._set_status(db, job, "transcribing")
                    transcript = self.transcriber.transcribe(source_path, self.storage_root / "captions", stem)

                outputs = []
                warnings = []
                platforms_failed = []

                for platform in chosen_platforms:
                    try:
                        preset = self.presets.get_preset(platform)
                        self._set_status(db, job, "rendering")
                        output_name = generate_output_filename(job.source_file_name, preset["output_suffix"])
                        out_path = self.storage_root / "processed" / output_name
                        sub = transcript["srt"] if transcript else None
                        self.renderer.render(source_path, out_path, preset, sub)

                        self._set_status(db, job, "uploading")
                        if self.cloud_mode and self.gcs:
                            drive_id = self.gcs.upload_output(out_path, f"processed/{output_name}")
                        else:
                            drive_id = self.drive.upload_file(out_path, settings.google_drive_processed_folder_id, output_name)

                        thumb_name = generate_thumbnail_filename(job.source_file_name, preset["output_suffix"])
                        thumb_path = self.storage_root / "thumbnails" / thumb_name
                        self.thumbnail.create(out_path, thumb_path)
                        if self.cloud_mode and self.gcs:
                            thumb_drive_id = self.gcs.upload_thumbnail(thumb_path, f"thumbnails/{thumb_name}")
                        else:
                            thumb_drive_id = self.drive.upload_file(thumb_path, settings.google_drive_thumbnails_folder_id, thumb_name)

                        row = JobOutput(
                            job_id=job.id,
                            platform=platform,
                            file_name=output_name,
                            drive_file_id=drive_id,
                            thumbnail_drive_file_id=thumb_drive_id,
                            duration_seconds=source_metadata.get("duration_seconds"),
                            width=int(preset["resolution"].split("x")[0]),
                            height=int(preset["resolution"].split("x")[1]),
                            file_size_mb=10.0,
                            status="completed",
                        )
                        db.add(row)
                        db.commit()
                        outputs.append({"platform": platform, "file_name": output_name, "drive_file_id": drive_id})
                    except Exception as ex:
                        platforms_failed.append(platform)
                        self._job_error(db, job.id, platform, "render_failed", str(ex))

                manifest_payload = {
                    "job_id": job.id,
                    "source_file_name": job.source_file_name,
                    "source_drive_file_id": job.source_drive_file_id,
                    "status": "completed" if not platforms_failed else "needs_review",
                    "source_metadata": source_metadata,
                    "subtitle_status": {
                        "detected": subtitle_status == "detected",
                        "mode_used": job.subtitle_mode,
                        "transcription_created": transcript is not None,
                    },
                    "transcript_file": str(transcript["srt"]) if transcript else None,
                    "outputs": outputs,
                    "thumbnails": [],
                    "errors": [],
                    "warnings": warnings,
                    "platforms_processed": [o["platform"] for o in outputs],
                    "platforms_failed": platforms_failed,
                    "webhook_status": "pending" if (webhook_url or settings.default_webhook_url) else "not_configured",
                    "completed_at": datetime.utcnow().isoformat(),
                }
                manifest_name = f"{stem}-manifest.json"
                manifest_path = self.storage_root / "manifests" / manifest_name
                self.manifest.create(manifest_path, manifest_payload)
                if self.cloud_mode and self.gcs:
                    manifest_drive_id = self.gcs.upload_manifest(manifest_path, f"manifests/{manifest_name}")
                else:
                    manifest_drive_id = self.drive.upload_file(manifest_path, settings.google_drive_manifests_folder_id, manifest_name)

                target_webhook = webhook_url or settings.default_webhook_url
                webhook_status = "not_sent"
                if target_webhook:
                    event_name = "job.completed" if not platforms_failed else "job.failed"
                    payload = {
                        "event": event_name,
                        "job_id": job.id,
                        "source_file_name": job.source_file_name,
                        "status": "completed" if not platforms_failed else "failed",
                        "manifest_drive_file_id": manifest_drive_id,
                        "outputs": outputs,
                    }
                    status, code = self.webhooks.send(target_webhook, payload)
                    webhook_status = status
                    db.add(WebhookEvent(job_id=job.id, event_type=event_name, webhook_url=target_webhook, payload_json=payload, status=status, response_code=code))
                    db.commit()

                job.manifest_drive_file_id = manifest_drive_id
                job.completed_at = datetime.utcnow()
                job.updated_at = datetime.utcnow()
                job.status = "completed" if not platforms_failed else "needs_review"
                db.commit()
                if self.firestore:
                    self.firestore.update_job(
                        job.id,
                        {
                            "status": job.status,
                            "manifest_uri": manifest_drive_id,
                            "outputs": outputs,
                            "platforms_failed": platforms_failed,
                            "completed_at": datetime.utcnow().isoformat(),
                        },
                    )
                logger.info("Manifest saved and uploaded. Webhook status: %s", webhook_status)

            except Exception as ex:
                self._fail(db, job, "job_failed", str(ex))

    def _should_transcribe(self, subtitle_mode: str, subtitle_status: str) -> bool:
        if subtitle_mode == "force_add":
            return True
        if subtitle_mode == "never_add":
            return False
        if subtitle_status == "detected":
            return False
        return True

    def _set_status(self, db, job: Job, status: str) -> None:
        if status not in VALID_STATUSES:
            raise ValueError(f"Invalid job status: {status}")
        job.status = status
        job.updated_at = datetime.utcnow()
        db.commit()
        if self.firestore:
            self.firestore.update_job(job.id, {"status": status})

    def _job_error(self, db, job_id: str, platform: str | None, code: str, message: str) -> None:
        db.add(JobError(job_id=job_id, platform=platform, error_code=code, error_message=message))
        db.commit()

    def _fail(self, db, job: Job, code: str, message: str) -> None:
        self._job_error(db, job.id, None, code, message)
        job.status = "failed"
        job.error_summary = message
        job.updated_at = datetime.utcnow()
        db.commit()
        if self.firestore:
            self.firestore.update_job(job.id, {"status": "failed", "error_summary": message, "error_code": code})