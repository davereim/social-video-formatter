# Social Video Formatter (Version 1)

API-first processing engine for converting one source video into platform-ready outputs.

## Primary V1 Deployment Target
- Google Cloud Run (API service)
- Google Cloud Run Jobs (video worker)
- Firestore (job status tracking)
- Cloud Storage (outputs, thumbnails, manifests)

## Non-Technical Quick Start (Local API)
1. Open this folder in File Explorer.
2. Double-click `run_api.bat`.
3. Open `http://127.0.0.1:8000/ui`.

## V1 Scope
- Create jobs from API.
- Trigger Cloud Run Job worker for processing.
- Store job status in Firestore.
- Store generated outputs in Cloud Storage.
- Keep Google Drive ingest support for source videos.

Not in V1:
- Social autoposting
- Scheduling
- AI-generated social captions/content
- Billing/multi-user SaaS

## Key Cloud Config
Set these in environment variables:
- `GCP_PROJECT_ID`
- `GCP_REGION`
- `FIRESTORE_JOBS_COLLECTION`
- `GCS_OUTPUT_BUCKET`
- `GCS_THUMBNAILS_BUCKET`
- `GCS_MANIFESTS_BUCKET`
- `CLOUD_RUN_JOB_NAME`

Also required:
- Google Drive OAuth values (`GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, `GOOGLE_REFRESH_TOKEN`)
- Google Drive folder IDs
- `APP_API_KEY`

## API Notes
- `POST /jobs?run_mode=cloud` (default): creates job + triggers Cloud Run Job.
- `POST /jobs?run_mode=local`: local background processing fallback.
- `GET /jobs?source=firestore` (default): reads from Firestore.
- `GET /jobs/{job_id}?source=firestore`.

## Cloud Deployment Files
- `Dockerfile`
- `cloudbuild.yaml`
- `deploy-cloud-run.txt`
- `.env.cloud.example`

## Deploy Outline (GCP)
1. Build image:
   - `gcloud builds submit --config cloudbuild.yaml`
2. Deploy API service:
   - Use command block in `deploy-cloud-run.txt`.
3. Deploy Cloud Run Job worker:
   - Use command block in `deploy-cloud-run.txt`.
4. Set env vars for both API and Job.
5. Call API `/health` and `/jobs`.

## Known V1 Limitations
- Smart cropping is basic.
- Subtitle detection is approximate.
- Rendering quality depends on FFmpeg command profile maturity.
- No direct social posting yet.
