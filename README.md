# Citation Format Checker

A domain Q&A chatbot that checks citation formatting for **APA 7th**, **MLA 9th**, and **Chicago 17th (Notes and Bibliography)**. Paste a passage or reference list and the bot identifies formatting violations with rule IDs and quoted evidence — without rewriting your text.

## Topic

Narrow domain: **citation and reference formatting** for the three major academic styles. The bot answers only questions about how citations and reference lists are formatted; it redirects off-topic requests (grammar, research quality, page layout) and includes a safety backstop for crisis language.

## Prerequisites

- Python 3.10+
- [uv](https://docs.astral.sh/uv/) for running the project
- Google Cloud with Vertex AI enabled

Create a `.env` file in this directory:

```
VERTEXAI_PROJECT=your-project-id
VERTEXAI_LOCATION=us-central1
```

## Running locally

```bash
uv run python app.py
```

Open http://localhost:8000 in your browser. Select a citation style (APA, MLA, or Chicago), paste your text, and click **Check**.

## API

- `GET /` — Serves the citation checker UI
- `POST /chat` — Body: `{ "message": "...", "session_id": null, "style": "apa" }`. Returns citation review.
- `POST /clear` — Optional `session_id` to clear that session

## Evaluation harness

Evals use deterministic checks (rule-ID and refusal keyword detection) and Model-as-a-Judge (golden reference and rubric). Single command:

```bash
uv run pytest evals/ -v
```

- **test_rules.py** — Deterministic: 10 in-domain (rule ID in response), 5 out-of-scope (redirect), 5 adversarial/safety. Prints pass rates by category.
- **test_golden.py** — 10+ golden-reference MaaJ evals (expected answer vs bot response), threshold ≥ 6/10.
- **test_rubric.py** — 10+ rubric MaaJ evals (weighted citation criteria), threshold ≥ 6/10.

Evals make live LLM calls and require network access and API credentials.

## Live deployment (GCP Cloud Run)

The app is deployed on Google Cloud Run and publicly accessible:

- **Live URL:** https://citation-bot-7pj7nolpla-uc.a.run.app
- **Project:** `agentic-ai-487000`
- **Region:** `us-central1`
- **Model:** Vertex AI `gemini-2.0-flash-lite`

### Deploying from scratch

1. **Authenticate and set the project:**

```bash
gcloud auth login
gcloud config set project agentic-ai-487000
```

2. **Enable required APIs:**

```bash
gcloud services enable run.googleapis.com artifactregistry.googleapis.com aiplatform.googleapis.com cloudbuild.googleapis.com
```

3. **Deploy from source (builds the Docker image via Cloud Build):**

```bash
gcloud run deploy citation-bot --source . --region=us-central1 --allow-unauthenticated --set-env-vars="VERTEXAI_PROJECT=agentic-ai-487000,VERTEXAI_LOCATION=us-central1"
```

4. **Grant Vertex AI permissions to the Cloud Run service account:**

```bash
PROJECT_NUMBER=$(gcloud projects describe agentic-ai-487000 --format="value(projectNumber)")
gcloud projects add-iam-policy-binding agentic-ai-487000 \
  --member="serviceAccount:${PROJECT_NUMBER}-compute@developer.gserviceaccount.com" \
  --role="roles/aiplatform.user"
```

### Redeploying after code changes

```bash
gcloud run deploy citation-bot --source . --region=us-central1 --project=agentic-ai-487000
```

## Repo contents

- `README.md` — This file (topic, run locally, evals, live URL)
- `pyproject.toml` — uv-based project config
- `app.py` — FastAPI backend and citation checker logic
- `index.html` — Simple web UI with style selector
- `evals/` — Pytest-based eval suite (golden, rubric, deterministic rules)
