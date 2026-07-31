# DataLens AI

Paste or upload raw/CSV data and get streamed, plain-language AI insights —
built with FastAPI, the Anthropic Claude API, Docker, and AWS App Runner.

## 1. Run locally

```bash
cd backend
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\Activate.ps1
pip install -r requirements.txt
cp .env.example .env            # then paste your real ANTHROPIC_API_KEY into .env
uvicorn main:app --reload --port 8000
```

Open http://localhost:8000 — the backend also serves the frontend directly.

## 2. Run with Docker (locally)

```bash
docker build -t datalens-ai .
docker run -p 8080:8080 --env-file backend/.env datalens-ai
```

Open http://localhost:8080

## 3. Push image to Amazon ECR

```bash
# One-time setup
aws configure                     # enter your AWS Access Key, Secret, region
aws ecr create-repository --repository-name datalens-ai

# Authenticate Docker to ECR (replace <account-id> and <region>)
aws ecr get-login-password --region <region> | \
  docker login --username AWS --password-stdin <account-id>.dkr.ecr.<region>.amazonaws.com

# Build, tag, push
docker build -t datalens-ai .
docker tag datalens-ai:latest <account-id>.dkr.ecr.<region>.amazonaws.com/datalens-ai:latest
docker push <account-id>.dkr.ecr.<region>.amazonaws.com/datalens-ai:latest
```

## 4. Deploy on AWS App Runner (free-tier friendly)

1. AWS Console → **App Runner** → **Create service**.
2. Source: **Container registry** → **Amazon ECR** → select `datalens-ai:latest`.
3. Deployment trigger: Manual (or Automatic if you want redeploy-on-push).
4. Port: `8080` (matches the Dockerfile `EXPOSE`).
5. Environment variables (Configure service → Environment variables):
   - `ANTHROPIC_API_KEY` = your real key (never commit this — set it here only)
   - `ANTHROPIC_MODEL` = `claude-sonnet-4-6`
   - `ALLOWED_ORIGINS` = your App Runner URL once known (or `*` while testing)
6. Instance size: smallest option (0.25 vCPU / 0.5 GB) is enough for this app.
7. Create & deploy. App Runner gives you a public HTTPS URL like
   `https://xxxxx.<region>.awsapprunner.com` — that's your live AWS URL for
   the Concept Note / Project Report.

## 5. Cost & safety guardrails

- Set an **AWS Budget alert** (Billing → Budgets → Create budget) at, e.g., $1
  so you're notified before any charge.
- App Runner's smallest instance + low traffic stays within/near free tier for
  a short-lived class project. Pause or delete the service after submission
  and grading if you don't need it running.
- The Anthropic API key is only ever read from environment variables — it
  never appears in `frontend/`, in Git history, or in the Docker image layers
  (`.dockerignore` excludes `.env`).

## Architecture

```
Browser (frontend/index.html)
   │  fetch() streaming POST /api/analyze
   ▼
FastAPI backend (backend/main.py)
   │  anthropic.messages.stream()
   ▼
Claude API (Anthropic)
```

Single Docker image serves both frontend (static files) and backend (API),
simplifying App Runner deployment to one container.
